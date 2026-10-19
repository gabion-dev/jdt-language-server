#!/usr/bin/env python3
# scripts/confirm-checksum.py
"""Confirm a milestone archive's SHA-256 with sources independent of Eclipse.

A checksum published next to the file proves nothing about the file: whoever
can replace one can replace the other. So the mirror publishes an archive only
when a package manager that pins the same Eclipse file by content states the
same SHA-256. Homebrew and the AUR both do; they are read from their own
repositories, not from download.eclipse.org.

Usage: confirm-checksum.py <version> <archive-file-name> <sha256>
Exit 0 when at least one source confirms and none contradicts; exit 1
otherwise, naming what each source said.
"""

import re
import sys
import urllib.request

SOURCES = {
    "Homebrew (Formula/j/jdtls.rb)":
        "https://raw.githubusercontent.com/Homebrew/homebrew-core/HEAD/Formula/j/jdtls.rb",
    "AUR (jdtls PKGBUILD)":
        "https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h=jdtls",
}


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "gabion-jdt-mirror"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def stated_sha256(text: str, version: str, archive: str) -> str | None:
    """The SHA-256 the source pins for this exact milestone file, or None
    when the source is at another version. Both sources name the file in
    their URL and pin one checksum for it."""
    if f"/jdtls/milestones/{version}/{archive}" not in text:
        return None
    homebrew = re.search(r'^\s*sha256 "([0-9a-f]{64})"', text, re.MULTILINE)
    if homebrew:
        return homebrew.group(1)
    aur = re.search(r"^sha256sums=\('([0-9a-f]{64})'\)", text, re.MULTILINE)
    if aur:
        return aur.group(1)
    raise ValueError("names the file but states no SHA-256 the script can read")


def main() -> int:
    version, archive, actual = sys.argv[1], sys.argv[2], sys.argv[3].lower()
    confirmed = 0
    contradicted = False
    for name, url in SOURCES.items():
        try:
            stated = stated_sha256(fetch(url), version, archive)
        except Exception as error:  # a source that cannot be read confirms nothing
            print(f"{name}: unreadable — {error}")
            continue
        if stated is None:
            print(f"{name}: does not list {archive} (another version)")
        elif stated == actual:
            print(f"{name}: confirms {actual}")
            confirmed += 1
        else:
            print(f"{name}: CONTRADICTS — states {stated}, the download is {actual}")
            contradicted = True
    if contradicted:
        print("A source independent of Eclipse states another checksum — not publishing.")
        return 1
    if confirmed == 0:
        print("No source independent of Eclipse confirms this file yet — not publishing.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
