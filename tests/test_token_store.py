import os
import tempfile
import unittest

from state.token_store import TokenStore, _ensure_schema, _path_is_usable


class TokenStorePathTest(unittest.TestCase):
    def test_path_is_usable_with_delete_journal_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, 'sessions.db')
            self.assertTrue(_path_is_usable(db_path))

            import sqlite3
            conn = sqlite3.connect(db_path)
            try:
                _ensure_schema(conn)
                row = conn.execute('PRAGMA journal_mode').fetchone()
                self.assertIn(row[0].lower(), ('wal', 'delete'))
            finally:
                conn.close()

    def test_token_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = TokenStore(db_path=os.path.join(tmp, 'sessions.db'))
            store.set(42, 'jwt-token', login='user42')
            self.assertEqual(store.get(42), 'jwt-token')
            self.assertEqual(store.get_login(42), 'user42')
            self.assertEqual(store.count(), 1)


if __name__ == '__main__':
    unittest.main()
