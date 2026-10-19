#!/usr/bin/env python3
# scripts/verify-launch.py
"""Start the unpacked server and complete one LSP handshake.

A file that exists proves nothing: the server is started the way Gabion
starts it (the Equinox launcher, the platform configuration directory, a
workspace data directory) on the `java` first on PATH and must answer
`initialize` with its capabilities, then shut down on `shutdown` and `exit`.

The launch is also the only reliable answer to "which Java does this
milestone need": the README and bin/jdtls.py of 1.62.0 still say 21 while
org.eclipse.core.filesystem requires JavaSE-25, and scanning manifests for
the newest execution environment overshoots, because optional bundles
(org.eclipse.jdt.core.javac asks for 25 already in 1.61.0, which runs on
21) may stay unresolved without stopping the server.

Usage: verify-launch.py <unpacked-server-dir> <scratch-dir>
"""

import glob
import json
import os
import subprocess
import sys
import threading

HANDSHAKE_TIMEOUT_S = 180  # a cold JVM and OSGi start on a CI runner


def frame(message: dict) -> bytes:
    body = json.dumps(message).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def read_message(stream) -> dict:
    length = None
    while True:
        line = stream.readline()
        if not line:
            raise EOFError("the server closed its output")
        line = line.strip()
        if not line:
            break
        name, _, value = line.decode("ascii").partition(":")
        if name.lower() == "content-length":
            length = int(value)
    if length is None:
        raise ValueError("message without Content-Length")
    return json.loads(stream.read(length))


def wait_for_response(stream, request_id: int) -> dict:
    while True:
        message = read_message(stream)
        if message.get("id") == request_id and "method" not in message:
            return message


def main() -> int:
    server_dir, scratch = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    launchers = glob.glob(os.path.join(server_dir, "plugins", "org.eclipse.equinox.launcher_*.jar"))
    if len(launchers) != 1:
        print(f"expected one Equinox launcher jar, found {launchers}")
        return 1
    project = os.path.join(scratch, "project")
    os.makedirs(project, exist_ok=True)
    command = [
        "java",
        "-Declipse.application=org.eclipse.jdt.ls.core.id1",
        "-Dosgi.bundles.defaultStartLevel=4",
        "-Declipse.product=org.eclipse.jdt.ls.core.product",
        "-Dlog.level=WARN",
        "--add-modules=ALL-SYSTEM",
        "--add-opens", "java.base/java.util=ALL-UNNAMED",
        "--add-opens", "java.base/java.lang=ALL-UNNAMED",
        "-jar", launchers[0],
        "-configuration", os.path.join(server_dir, "config_linux"),
        "-data", os.path.join(scratch, "data"),
    ]
    server = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    outcome: dict = {}

    def handshake() -> None:
        try:
            server.stdin.write(frame({
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"processId": os.getpid(), "rootUri": f"file://{project}", "capabilities": {}},
            }))
            server.stdin.flush()
            response = wait_for_response(server.stdout, 1)
            outcome["capabilities"] = response.get("result", {}).get("capabilities")
            outcome["error"] = response.get("error")
            server.stdin.write(frame({"jsonrpc": "2.0", "method": "initialized", "params": {}}))
            server.stdin.write(frame({"jsonrpc": "2.0", "id": 2, "method": "shutdown"}))
            server.stdin.flush()
            wait_for_response(server.stdout, 2)
            server.stdin.write(frame({"jsonrpc": "2.0", "method": "exit"}))
            server.stdin.flush()
            outcome["shutdown"] = True
        except Exception as error:
            outcome["failure"] = repr(error)

    worker = threading.Thread(target=handshake, daemon=True)
    worker.start()
    worker.join(HANDSHAKE_TIMEOUT_S)
    try:
        code = server.wait(timeout=30)
    except subprocess.TimeoutExpired:
        server.kill()
        code = None
    if worker.is_alive():
        print(f"no handshake within {HANDSHAKE_TIMEOUT_S} s")
        return 1
    if "failure" in outcome or outcome.get("error") or not outcome.get("capabilities"):
        print(f"handshake failed: {outcome}")
        return 1
    print(f"initialize answered with {len(outcome['capabilities'])} capabilities; shutdown acknowledged; exit code {code}")
    if code != 0:
        print("the server did not exit cleanly after exit")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
