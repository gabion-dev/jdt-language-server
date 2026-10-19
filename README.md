# JDT Language Server Mirror

Mirror of Eclipse JDT Language Server milestone builds for deterministic installation by [Gabion](https://github.com/gabion-dev).

Eclipse milestone builds are hosted on `download.eclipse.org` behind a CDN that occasionally returns transient errors. This mirror provides permanent, CDN-backed URLs via GitHub Releases for reliable automated installation.

## Source

Archives are downloaded from [Eclipse JDT LS milestones](https://download.eclipse.org/jdtls/milestones/) and published here without modification, renamed to `jdt-language-server-<version>.tar.gz`.

## How a release is made

Releases are made by the [release workflow](.github/workflows/release.yml) (Actions → Mirror a JDT LS milestone → Run workflow), never by hand. It publishes a milestone only when:

- the archive is the one Eclipse names for the milestone (`latest.txt`) and matches the `.sha256` beside it;
- a source independent of Eclipse — the Homebrew formula or the AUR package of `jdtls` — pins the same file with the same SHA-256 ([scripts/confirm-checksum.py](scripts/confirm-checksum.py));
- the server starts on the Java version given to the workflow and completes an LSP handshake ([scripts/verify-launch.py](scripts/verify-launch.py)). The project's README is not trusted for the Java it needs: 1.62.0 states 21 but requires 25.

A published release is never rewritten: installers build its address from the version.

## License

Eclipse JDT Language Server is licensed under the [Eclipse Public License 2.0](https://www.eclipse.org/legal/epl-2.0/). The Eclipse archive carries the license only inside its plugin jars, so every release of this mirror also publishes the license text as a `LICENSE` asset next to the archive (the [LICENSE](LICENSE) file of this repository), and the installer places it beside the server.

See [eclipse-jdtls/eclipse.jdt.ls](https://github.com/eclipse-jdtls/eclipse.jdt.ls) for the source code.