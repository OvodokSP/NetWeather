from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
import time
from pathlib import Path

DB_PATH = Path(os.getenv("NETWEATHER_DB", "/data/netweather.db"))


def _integrity_check(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    with sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True) as conn:
        result = conn.execute("PRAGMA integrity_check").fetchone()
    if not result or result[0] != "ok":
        raise RuntimeError(f"SQLite integrity_check failed for {path}")


def backup_database(source: str | Path, destination: str | Path) -> Path:
    """Create a transactionally consistent SQLite snapshot and verify it."""
    source_path, destination_path = Path(source), Path(destination)
    if source_path.resolve() == destination_path.resolve():
        raise ValueError("backup source and destination must differ")
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".netweather-backup-", suffix=".sqlite", dir=destination_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with sqlite3.connect(source_path, timeout=15) as source_db, sqlite3.connect(temp_path) as backup_db:
            source_db.backup(backup_db)
        _integrity_check(temp_path)
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, destination_path)
        return destination_path
    finally:
        temp_path.unlink(missing_ok=True)


def restore_database(source: str | Path, destination: str | Path, *, offline_confirmed: bool = False) -> Path:
    """Restore a verified snapshot; caller must stop the app first.

    A pre-restore SQLite snapshot is kept beside the target so failed verification
    can be rolled back without depending on a second machine or service.
    """
    source_path, destination_path = Path(source), Path(destination)
    if not offline_confirmed:
        raise RuntimeError("restore requires the application to be stopped and --offline-confirmed")
    if source_path.resolve() == destination_path.resolve():
        raise ValueError("restore source and destination must differ")
    _integrity_check(source_path)
    for suffix in ("-wal", "-shm"):
        if Path(str(destination_path) + suffix).exists():
            raise RuntimeError(f"remove/check SQLite sidecar {destination_path}{suffix}; restore target is not quiescent")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    rollback_path = None
    if destination_path.exists():
        rollback_path = destination_path.with_name(
            f"{destination_path.name}.pre-restore-{int(time.time())}.sqlite"
        )
        backup_database(destination_path, rollback_path)
    fd, temp_name = tempfile.mkstemp(prefix=".netweather-restore-", suffix=".sqlite", dir=destination_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        backup_database(source_path, temp_path)
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, destination_path)
        _integrity_check(destination_path)
        return destination_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        if rollback_path and rollback_path.exists():
            os.replace(rollback_path, destination_path)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite-safe NetWeather database backup/restore")
    subparsers = parser.add_subparsers(dest="action", required=True)
    backup = subparsers.add_parser("backup")
    backup.add_argument("--source", type=Path, default=DB_PATH)
    backup.add_argument("--destination", type=Path, required=True)
    restore = subparsers.add_parser("restore")
    restore.add_argument("--source", type=Path, required=True)
    restore.add_argument("--destination", type=Path, default=DB_PATH)
    restore.add_argument("--offline-confirmed", action="store_true",
                         help="confirm the service is stopped and the SQLite target is quiescent")
    args = parser.parse_args()
    if args.action == "backup":
        path = backup_database(args.source, args.destination)
    else:
        path = restore_database(args.source, args.destination, offline_confirmed=args.offline_confirmed)
    print(f"PASS {args.action}: {path}")


if __name__ == "__main__":
    main()
