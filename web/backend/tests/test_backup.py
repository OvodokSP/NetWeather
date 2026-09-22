import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.backup import backup_database, restore_database


class DatabaseBackupTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.database = self.root / "netweather.sqlite"
        with sqlite3.connect(self.database) as conn:
            conn.execute("CREATE TABLE samples (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
            conn.execute("INSERT INTO samples(value) VALUES ('before')")

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_value(self, path):
        with sqlite3.connect(path) as conn:
            return conn.execute("SELECT value FROM samples").fetchone()[0]

    def test_backup_is_integral_private_and_restorable(self):
        backup = backup_database(self.database, self.root / "backups" / "snapshot.sqlite")
        self.assertEqual(self.read_value(backup), "before")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

        with sqlite3.connect(self.database) as conn:
            conn.execute("UPDATE samples SET value='after'")
        restore_database(backup, self.database, offline_confirmed=True)

        self.assertEqual(self.read_value(self.database), "before")
        self.assertTrue(list(self.root.glob("netweather.sqlite.pre-restore-*.sqlite")))

    def test_restore_requires_explicit_quiescence_confirmation(self):
        backup = backup_database(self.database, self.root / "snapshot.sqlite")
        with self.assertRaisesRegex(RuntimeError, "offline-confirmed"):
            restore_database(backup, self.database)

    def test_backup_rejects_same_source_and_destination(self):
        with self.assertRaisesRegex(ValueError, "must differ"):
            backup_database(self.database, self.database)

    def test_restore_rejects_sqlite_sidecars(self):
        backup = backup_database(self.database, self.root / "snapshot.sqlite")
        Path(str(self.database) + "-wal").touch()
        with self.assertRaisesRegex(RuntimeError, "not quiescent"):
            restore_database(backup, self.database, offline_confirmed=True)


if __name__ == "__main__":
    unittest.main()
