import tempfile
import unittest
import tempfile
from pathlib import Path

from backend.services.ragflow_chat_service import RagflowChatService
from backend.services.ragflow_connection import RagflowConnection


class _FakeHttp:
    def __init__(self):
        self.put_calls = []
        self._calls = 0

    def set_config(self, _cfg):  # noqa: ARG002
        return None

    def put_json(self, path, body=None, params=None):  # noqa: ARG002
        self.put_calls.append((path, body))
        self._calls += 1
        if self._calls == 1:
            return {
                "code": 100,
                "message": "The dataset abc doesn't own parsed file",
                "data": None,
            }
        return {"code": 0, "data": {"id": "c1", **(body or {})}}


class TestRagflowChatUpdateRetryUnit(unittest.TestCase):
    def test_update_chat_retries_minimal_on_parsed_file_ownership_error(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "ragflow_config.json"
            cfg_path.write_text('{"base_url":"http://127.0.0.1:9380","api_key":"k","timeout":10}', encoding="utf-8")

            fake_http = _FakeHttp()
            conn = RagflowConnection(config_path=cfg_path, config={"base_url": "http://127.0.0.1:9380", "api_key": "k", "timeout": 10}, http=fake_http)
            svc = RagflowChatService(connection=conn)

            payload = {
                "name": "n1",
                "dataset_ids": ["d1", "d2"],
                # This field is not stripped by sanitize and simulates a "hidden binding"
                # that some RAGFlow versions reject when dataset ownership changes.
                "parsed_files": ["pf1"],
            }
            out = svc.update_chat("c1", payload)
            self.assertIsInstance(out, dict)
            self.assertEqual(out.get("id"), "c1")

            self.assertEqual(len(fake_http.put_calls), 2)
            _path1, body1 = fake_http.put_calls[0]
            _path2, body2 = fake_http.put_calls[1]
            self.assertIn("parsed_files", body1)
            # Retry must be minimal.
            self.assertNotIn("parsed_files", body2)
            self.assertEqual(body2.get("dataset_ids"), ["d1", "d2"])
            self.assertEqual(body2.get("name"), "n1")

    def test_update_chat_refetches_when_put_returns_none_but_applied(self):
        class _ApplyButNoResponseHttp:
            def __init__(self):
                self._stored = {"id": "c9", "name": "old", "dataset_ids": ["d0"]}
                self.put_calls = 0

            def set_config(self, _cfg):  # noqa: ARG002
                return None

            def put_json(self, _path, body=None, params=None):  # noqa: ARG002
                self.put_calls += 1
                # Simulate server applied update but client couldn't parse the response.
                if isinstance(body, dict):
                    if "name" in body:
                        self._stored["name"] = body["name"]
                    if "dataset_ids" in body:
                        self._stored["dataset_ids"] = list(body["dataset_ids"])
                return None

            def get_list(self, path, params=None, context=None):  # noqa: ARG002
                # get_chat() calls list_chats(chat_id=...)
                if path == "/api/v1/chats" and isinstance(params, dict) and params.get("id") == "c9":
                    return [dict(self._stored)]
                return []

        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "ragflow_config.json"
            cfg_path.write_text('{"base_url":"http://127.0.0.1:9380","api_key":"k","timeout":10}', encoding="utf-8")

            http = _ApplyButNoResponseHttp()
            conn = RagflowConnection(
                config_path=cfg_path,
                config={"base_url": "http://127.0.0.1:9380", "api_key": "k", "timeout": 10},
                http=http,
            )
            svc = RagflowChatService(connection=conn)
            out = svc.update_chat("c9", {"name": "new", "dataset_ids": ["d1"]})
            self.assertIsInstance(out, dict)
            self.assertEqual(out.get("id"), "c9")
            self.assertEqual(out.get("name"), "new")
            self.assertEqual(out.get("dataset_ids"), ["d1"])

    def test_update_chat_raises_stable_code_when_locked(self):
        class _AlwaysFailHttp:
            def set_config(self, _cfg):  # noqa: ARG002
                return None

            def put_json(self, _path, body=None, params=None):  # noqa: ARG002
                return {"code": 100, "message": "The dataset abc doesn't own parsed file", "data": None}

            def get_json(self, _path, params=None):  # noqa: ARG002
                return {"code": 0, "data": []}

            def get_list(self, _path, params=None, context=None):  # noqa: ARG002
                return []

        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "ragflow_config.json"
            cfg_path.write_text('{"base_url":"http://127.0.0.1:9380","api_key":"k","timeout":10}', encoding="utf-8")
            conn = RagflowConnection(
                config_path=cfg_path,
                config={"base_url": "http://127.0.0.1:9380", "api_key": "k", "timeout": 10},
                http=_AlwaysFailHttp(),
            )
            svc = RagflowChatService(connection=conn)
            with self.assertRaises(ValueError) as ctx:
                svc.update_chat("c1", {"name": "n1", "dataset_ids": ["d1"]})
            self.assertIn("chat_dataset_locked", str(ctx.exception))

    def test_clear_chat_parsed_files_clears_only_existing_fields(self):
        class _Http:
            def __init__(self):
                self.put_calls = []

            def set_config(self, _cfg):  # noqa: ARG002
                return None

            def get_list(self, path, params=None, context=None):  # noqa: ARG002
                if path == "/api/v1/chats" and isinstance(params, dict) and params.get("id") == "c_pf":
                    return [
                        {
                            "id": "c_pf",
                            "name": "n",
                            "dataset_ids": ["d1"],
                            # Two possible parsed-file binding shapes.
                            "parsed_files": ["pf1", "pf2"],
                            "parsed_file_id": "pf_single",
                            # Should not be touched.
                            "other": "x",
                        }
                    ]
                return []

            def put_json(self, path, body=None, params=None):  # noqa: ARG002
                self.put_calls.append((path, body))
                return {"code": 0, "data": {"id": "c_pf", **(body or {})}}

        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "ragflow_config.json"
            cfg_path.write_text('{"base_url":"http://127.0.0.1:9380","api_key":"k","timeout":10}', encoding="utf-8")
            http = _Http()
            conn = RagflowConnection(
                config_path=cfg_path,
                config={"base_url": "http://127.0.0.1:9380", "api_key": "k", "timeout": 10},
                http=http,
            )
            svc = RagflowChatService(connection=conn)

            out = svc.clear_chat_parsed_files("c_pf")
            self.assertIsInstance(out, dict)
            self.assertEqual(out.get("id"), "c_pf")
            self.assertEqual(len(http.put_calls), 1)

            _path, body = http.put_calls[0]
            self.assertEqual(_path, "/api/v1/chats/c_pf")
            self.assertIsInstance(body, dict)
            # Do not send identity fields.
            self.assertNotIn("id", body)
            # Keep dataset linkage stable.
            self.assertEqual(body.get("dataset_ids"), ["d1"])
            # Clear only parsed-file binding fields that exist.
            self.assertEqual(body.get("parsed_files"), [])
            self.assertEqual(body.get("parsed_file_id"), "")


class _FakeHttpMerge:
    def __init__(self):
        self.put_calls = []
        self._calls = 0

    def set_config(self, _cfg):  # noqa: ARG002
        return None

    def get_list(self, path, params=None, context=None):  # noqa: ARG002
        # Simulate get_chat() -> list_chats(chat_id=...)
        if path == "/api/v1/chats":
            raw_id = None
            if isinstance(params, dict):
                raw_id = params.get("id")
            if raw_id:
                return [{"id": raw_id, "dataset_ids": ["d_old"]}]
        return []

    def put_json(self, path, body=None, params=None):  # noqa: ARG002
        self.put_calls.append((path, body))
        self._calls += 1
        # 1st: full update fails
        if self._calls == 1:
            return {"code": 100, "message": "The dataset d_new doesn't own parsed file", "data": None}
        # 2nd: minimal update with only d_new still fails
        if self._calls == 2:
            return {"code": 100, "message": "The dataset d_new doesn't own parsed file", "data": None}
        # 3rd: merged dataset_ids must include d_old to succeed
        ds = (body or {}).get("dataset_ids") or []
        if isinstance(ds, list) and ("d_old" in ds) and ("d_new" in ds):
            return {"code": 0, "data": {"id": "c2", **(body or {})}}
        return {"code": 100, "message": "The dataset still doesn't own parsed file", "data": None}


class TestRagflowChatUpdateMergeRetryUnit(unittest.TestCase):
    def test_update_chat_merges_current_dataset_ids_when_needed(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_path = Path(td) / "ragflow_config.json"
            cfg_path.write_text('{"base_url":"http://127.0.0.1:9380","api_key":"k","timeout":10}', encoding="utf-8")

            fake_http = _FakeHttpMerge()
            conn = RagflowConnection(config_path=cfg_path, config={"base_url": "http://127.0.0.1:9380", "api_key": "k", "timeout": 10}, http=fake_http)
            svc = RagflowChatService(connection=conn)

            out = svc.update_chat("c2", {"name": "n2", "dataset_ids": ["d_new"]})
            self.assertEqual(out.get("id"), "c2")
            self.assertEqual(len(fake_http.put_calls), 3)
            _p3, b3 = fake_http.put_calls[2]
            self.assertEqual(sorted(b3.get("dataset_ids")), ["d_new", "d_old"])
