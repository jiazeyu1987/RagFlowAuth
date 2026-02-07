import unittest
from pathlib import Path

from backend.database.schema.ensure import ensure_schema
from backend.services.chat_message_sources_store import ChatMessageSourcesStore, content_hash_hex
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestChatMessageSourcesStoreUnit(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = make_temp_dir(prefix="ragflowauth_test_chat_sources")
        self._db_path = self._tmp / "auth.db"
        ensure_schema(self._db_path)
        self._store = ChatMessageSourcesStore(db_path=str(self._db_path))

    def tearDown(self) -> None:
        cleanup_dir(self._tmp)

    def test_hash_strips_think_tags(self):
        raw = "<think>secret</think>Hello\\nWorld"
        stripped = "Hello\\nWorld"
        self.assertEqual(content_hash_hex(raw), content_hash_hex(stripped))

    def test_upsert_and_get_sources_map(self):
        chat_id = "c1"
        session_id = "s1"
        assistant_text = "Answer with [ID:1]"
        sources = [{"doc_id": "d1", "dataset": "kb1", "filename": "f1", "chunk": "chunk1"}]

        self._store.upsert_sources(
            chat_id=chat_id,
            session_id=session_id,
            assistant_text=assistant_text,
            sources=sources,
        )

        h = content_hash_hex(assistant_text)
        got = self._store.get_sources_map(chat_id=chat_id, session_id=session_id, content_hashes=[h])
        self.assertIn(h, got)
        self.assertEqual(got[h], sources)

