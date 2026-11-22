"""Coordinated Compose backup and restore to an empty, isolated project."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from tempfile import TemporaryDirectory

ARTIFACTS = ("database.dump", "private-pdfs.tar")
APP_SERVICES = ("gateway", "api", "indexer", "expiry")
DB_EXEC = ("exec", "-T", "db")
PDF_EXEC = ("run", "--rm", "--no-deps", "-T", "indexer")


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--project", required=True)
    parser.add_argument("--env-file", required=True)
    args = parser.parse_args()
    base = [
        "docker",
        "compose",
        "--project-name",
        args.project,
        "--env-file",
        args.env_file,
        "-f",
        "compose.production.yaml",
    ]

    def compose(*parameters, **kwargs):
        return subprocess.run([*base, *parameters], check=True, **kwargs)

    directory = args.directory.resolve()
    started = time.monotonic()
    if args.action == "backup":
        if directory.exists():
            raise SystemExit("Choose a new backup directory")
        running = compose(
            "ps", "--services", "--status", "running", capture_output=True, text=True
        ).stdout.split()
        paused = [service for service in APP_SERVICES if service in running]
        if paused:
            compose("stop", *paused)
        try:
            directory.parent.mkdir(parents=True, exist_ok=True)
            with TemporaryDirectory(dir=directory.parent) as temporary:
                target = Path(temporary)
                with (target / ARTIFACTS[0]).open("wb") as dump:
                    compose(
                        *DB_EXEC,
                        "sh",
                        "-ec",
                        'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"',
                        stdout=dump,
                    )
                with (target / ARTIFACTS[1]).open("wb") as archive:
                    compose(
                        *PDF_EXEC,
                        "tar",
                        "-C",
                        "/private-pdfs",
                        "-cf",
                        "-",
                        ".",
                        stdout=archive,
                    )
                manifest = {name: checksum(target / name) for name in ARTIFACTS}
                directory.mkdir(mode=0o700)
                for name in ARTIFACTS:
                    (target / name).replace(directory / name)
                (directory / "sha256.json").write_text(json.dumps(manifest, indent=2))
        finally:
            if paused:
                compose("start", *reversed(paused))
    else:
        manifest = json.loads((directory / "sha256.json").read_text())
        if any(checksum(directory / name) != manifest.get(name) for name in ARTIFACTS):
            raise SystemExit("Backup checksum mismatch")
        running = compose(
            "ps", "--services", "--status", "running", capture_output=True, text=True
        ).stdout.split()
        if set(running) - {"db"}:
            raise SystemExit("Restore requires an isolated target with only db running")
        compose("up", "-d", "--wait", "db")
        empty = compose(
            *DB_EXEC,
            "sh",
            "-ec",
            'psql -X -tA -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" '
            '-d "$POSTGRES_DB" -c "SELECT count(*) FROM pg_class c '
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public'\"",
            capture_output=True,
            text=True,
        ).stdout.strip()
        if empty != "0":
            raise SystemExit("Restore requires an empty database")
        compose(*PDF_EXEC, "sh", "-ec", 'test -z "$(ls -A /private-pdfs)"')
        with (directory / ARTIFACTS[0]).open("rb") as dump:
            compose(
                *DB_EXEC,
                "sh",
                "-ec",
                'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
                "--no-owner --no-privileges --exit-on-error --single-transaction",
                stdin=dump,
            )
        with (directory / ARTIFACTS[1]).open("rb") as archive:
            compose(
                *PDF_EXEC,
                "tar",
                "-C",
                "/private-pdfs",
                "-xf",
                "-",
                "--no-same-owner",
                stdin=archive,
            )
        compose("up", "-d", "--wait")
    print(f"{args.action} completed in {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    main()
