"""Persistent bot sessions in SQLite (survives container restarts)."""

import json
import os
import sqlite3
import threading
import time
from typing import List, Optional


def _app_data_db_path() -> str:
    return '/app/data/sessions.db'


def _default_db_path() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'data', 'sessions.db')
    )


def _home_db_path() -> str:
    return os.path.join(
        os.path.expanduser('~'),
        '.local',
        'share',
        'swingfox',
        'sessions.db',
    )


def _shm_db_path() -> str:
    return '/dev/shm/swingfox/sessions.db'


def _candidate_paths(requested: Optional[str] = None) -> List[str]:
    paths: List[str] = []
    if requested:
        paths.append(os.path.abspath(requested))

    env_path = os.getenv('SESSION_DB_PATH') or os.getenv('TOKEN_STORE_PATH')
    if env_path:
        paths.append(os.path.abspath(env_path))

    paths.extend([
        _app_data_db_path(),
        _shm_db_path(),
        _default_db_path(),
        _home_db_path(),
    ])

    unique: List[str] = []
    seen = set()
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _ensure_schema(conn: sqlite3.Connection) -> None:
    for journal_mode in ('WAL', 'DELETE'):
        try:
            conn.execute(f'PRAGMA journal_mode={journal_mode}')
            break
        except sqlite3.Error:
            if journal_mode == 'DELETE':
                raise
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS sessions (
          telegram_id INTEGER PRIMARY KEY,
          token TEXT,
          login TEXT,
          updated_at INTEGER NOT NULL
        )
        '''
    )
    conn.commit()


def _path_is_usable(path: str) -> bool:
    directory = os.path.dirname(path) or '.'
    try:
        os.makedirs(directory, exist_ok=True)
        probe = os.path.join(directory, '.write_probe')
        with open(probe, 'w', encoding='utf-8') as handle:
            handle.write('1')
        os.remove(probe)
    except OSError as exc:
        print(f'WARNING: session directory not writable ({directory}): {exc}')
        return False

    try:
        conn = sqlite3.connect(path, timeout=5)
        try:
            _ensure_schema(conn)
        finally:
            conn.close()
        return True
    except (OSError, sqlite3.Error) as exc:
        print(f'WARNING: SQLite path not usable ({path}): {exc}')
        return False


_MEMORY_DB_URI = 'file:swingfox_sessions?mode=memory&cache=shared'


def _resolve_db_path(requested: Optional[str] = None) -> str:
    candidates = _candidate_paths(requested)
    for path in candidates:
        if _path_is_usable(path):
            return path

    print(
        'WARNING: no writable session directory (disk full?). '
        'Using in-memory SQLite — sessions will be lost on restart. '
        'Free disk space: docker system prune -af && df -h'
    )
    return _MEMORY_DB_URI


class TokenStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path in (':memory:', _MEMORY_DB_URI):
            self._db_path = _MEMORY_DB_URI
            self._persistent = False
        else:
            self._db_path = _resolve_db_path(db_path)
            self._persistent = not self._db_path.startswith('file:swingfox_sessions')
        self._lock = threading.Lock()
        self._init_storage()
        if self._persistent:
            print(f'Session DB: {self._db_path}')
        else:
            print('Session DB: in-memory (not persistent)')
        self._migrate_json_if_needed()

    @property
    def db_path(self) -> str:
        return self._db_path

    @property
    def persistent(self) -> bool:
        return self._persistent

    def _init_storage(self) -> None:
        with self._connect() as conn:
            _ensure_schema(conn)

    def _connect(self) -> sqlite3.Connection:
        if self._db_path.startswith('file:'):
            conn = sqlite3.connect(self._db_path, timeout=30, uri=True)
        else:
            conn = sqlite3.connect(self._db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _legacy_json_path(self) -> str:
        paths: List[str] = []
        if not self._db_path.startswith('file:'):
            paths.append(os.path.join(os.path.dirname(self._db_path), 'tokens.json'))
        paths.extend([
            '/app/data/tokens.json',
            '/data/tokens.json',
            os.path.join(os.path.dirname(__file__), '..', 'data', 'tokens.json'),
        ])
        for path in paths:
            if os.path.isfile(path):
                return path
        return paths[0]

    def _migrate_json_if_needed(self) -> None:
        if self.count() > 0:
            return

        legacy_path = self._legacy_json_path()
        if not os.path.isfile(legacy_path):
            return

        try:
            with open(legacy_path, 'r', encoding='utf-8') as handle:
                raw = json.load(handle)
        except Exception as exc:
            print(f'WARNING: failed to migrate legacy token store ({legacy_path}): {exc}')
            return

        imported = 0
        now = int(time.time())
        with self._lock, self._connect() as conn:
            for key, token in raw.items():
                if not token:
                    continue
                conn.execute(
                    '''
                    INSERT OR REPLACE INTO sessions (telegram_id, token, login, updated_at)
                    VALUES (?, ?, NULL, ?)
                    ''',
                    (int(key), token, now),
                )
                imported += 1
            conn.commit()

        if imported:
            print(f'Migrated {imported} session(s) from {legacy_path} to {self._db_path}')

    def get(self, telegram_id: int) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT token FROM sessions WHERE telegram_id = ?',
                (int(telegram_id),),
            ).fetchone()
        token = row['token'] if row else None
        return token or None

    def get_login(self, telegram_id: int) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                'SELECT login FROM sessions WHERE telegram_id = ?',
                (int(telegram_id),),
            ).fetchone()
        login = row['login'] if row else None
        return login or None

    def set(self, telegram_id: int, token: str, login: Optional[str] = None) -> None:
        now = int(time.time())
        with self._lock, self._connect() as conn:
            if login is None:
                row = conn.execute(
                    'SELECT login FROM sessions WHERE telegram_id = ?',
                    (int(telegram_id),),
                ).fetchone()
                login = row['login'] if row else None

            conn.execute(
                '''
                INSERT INTO sessions (telegram_id, token, login, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                  token = excluded.token,
                  login = COALESCE(excluded.login, sessions.login),
                  updated_at = excluded.updated_at
                ''',
                (int(telegram_id), token, login, now),
            )
            conn.commit()

    def set_login(self, telegram_id: int, login: str) -> None:
        now = int(time.time())
        with self._lock, self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO sessions (telegram_id, token, login, updated_at)
                VALUES (?, NULL, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                  login = excluded.login,
                  updated_at = excluded.updated_at
                ''',
                (int(telegram_id), login, now),
            )
            conn.commit()

    def pop(self, telegram_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                '''
                UPDATE sessions
                SET token = NULL, updated_at = ?
                WHERE telegram_id = ?
                ''',
                (int(time.time()), int(telegram_id)),
            )
            conn.commit()

    def delete(self, telegram_id: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute('DELETE FROM sessions WHERE telegram_id = ?', (int(telegram_id),))
            conn.commit()

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS total FROM sessions WHERE token IS NOT NULL AND token != ''"
            ).fetchone()
        return int(row['total']) if row else 0


_store: Optional[TokenStore] = None
_store_lock = threading.Lock()


def get_token_store() -> TokenStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = TokenStore()
    return _store


class _TokenStoreProxy:
    def __getattr__(self, name: str):
        return getattr(get_token_store(), name)


token_store = _TokenStoreProxy()
