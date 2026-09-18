import unittest
from unittest import mock
from urllib.parse import parse_qsl, urlsplit

from app.db.database import _build_async_engine


class DatabaseSslTest(unittest.TestCase):
    def test_neon_postgres_ssl_injected(self):
        neon_url = "postgresql://neondb_owner:secret@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require"
        with mock.patch("app.db.database.settings") as mock_settings:
            mock_settings.database_url = neon_url
            with mock.patch("app.db.database.create_async_engine") as mock_create_engine:
                _build_async_engine()
                self.assertTrue(mock_create_engine.called)
                called_url = mock_create_engine.call_args[0][0]
                called_kwargs = mock_create_engine.call_args[1]

                # Scheme should be postgresql+asyncpg
                self.assertTrue(called_url.startswith("postgresql+asyncpg://"))
                # Query params should have ssl=require, not sslmode
                parts = urlsplit(called_url)
                query_dict = dict(parse_qsl(parts.query))
                self.assertEqual(query_dict.get("ssl"), "require")
                self.assertNotIn("sslmode", query_dict)
                # connect_args should contain ssl: require
                self.assertEqual(called_kwargs.get("connect_args", {}).get("ssl"), "require")
                self.assertTrue(called_kwargs.get("pool_pre_ping"))
                self.assertEqual(called_kwargs.get("pool_recycle"), 300)

    def test_sqlite_url_untouched(self):
        sqlite_url = "sqlite+aiosqlite:///./test.db"
        with mock.patch("app.db.database.settings") as mock_settings:
            mock_settings.database_url = sqlite_url
            with mock.patch("app.db.database.create_async_engine") as mock_create_engine:
                _build_async_engine()
                called_url = mock_create_engine.call_args[0][0]
                called_kwargs = mock_create_engine.call_args[1]

                self.assertEqual(called_url, sqlite_url)
                self.assertEqual(called_kwargs.get("connect_args"), {})


if __name__ == "__main__":
    unittest.main()
