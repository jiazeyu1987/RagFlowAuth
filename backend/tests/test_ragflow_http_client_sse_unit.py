import unittest
from unittest.mock import patch

import requests

from backend.services.ragflow_http_client import RagflowHttpClient, RagflowHttpClientConfig


class _FakeSseResponse:
    def __init__(self):
        self.status_code = 200
        self.closed = False

    def iter_lines(self, *args, **kwargs):
        yield b'data: {"code":0,"data":{"answer":"hello"}}'
        raise requests.exceptions.ChunkedEncodingError("Response ended prematurely")

    def close(self):
        self.closed = True


class _FakeSsePlainTextResponse:
    def __init__(self):
        self.status_code = 200
        self.closed = False

    def iter_lines(self, *args, **kwargs):
        yield b"data: hello from upstream"
        yield b"data: [DONE]"

    def close(self):
        self.closed = True


class _FakeSseChoicesDeltaResponse:
    def __init__(self):
        self.status_code = 200
        self.closed = False

    def iter_lines(self, *args, **kwargs):
        yield b'data: {"choices":[{"delta":{"content":"delta token"}}]}'
        yield b"data: [DONE]"

    def close(self):
        self.closed = True


class _FakeSseSingleQuoteDictResponse:
    def __init__(self):
        self.status_code = 200
        self.closed = False

    def iter_lines(self, *args, **kwargs):
        yield b"data: {'data': {'answer': 'single-quote answer'}}"
        yield b"data: [DONE]"

    def close(self):
        self.closed = True


class _FakeSseMultilineEventResponse:
    def __init__(self):
        self.status_code = 200
        self.closed = False

    def iter_lines(self, *args, **kwargs):
        yield b'data: {"code":0,'
        yield b'data: "data":{"answer":"multi-line answer"}}'
        yield b""
        yield b"data: [DONE]"

    def close(self):
        self.closed = True


class _FakeSseNoBlankTerminatorResponse:
    def __init__(self):
        self.status_code = 200
        self.closed = False

    def iter_lines(self, *args, **kwargs):
        yield b'data: {"code":0,"data":{"answer":"tail flush answer"}}'
        # no blank line / no [DONE]

    def close(self):
        self.closed = True


class _FakeSseConsecutiveDataNoBlankResponse:
    def __init__(self):
        self.status_code = 200
        self.closed = False

    def iter_lines(self, *args, **kwargs):
        yield b'data: {"code":0,"data":{"answer":"token-1"}}'
        yield b'data: {"code":0,"data":{"answer":"token-2"}}'
        yield b"data: [DONE]"

    def close(self):
        self.closed = True


class TestRagflowHttpClientSseUnit(unittest.TestCase):
    def test_post_sse_handles_chunked_disconnect_without_throwing(self):
        client = RagflowHttpClient(
            RagflowHttpClientConfig(base_url="http://127.0.0.1:9380", api_key="k", timeout_s=5.0)
        )
        fake_resp = _FakeSseResponse()

        with patch("backend.services.ragflow_http_client.requests.post", return_value=fake_resp):
            events = list(client.post_sse("/api/v1/chats/c1/completions", body={"question": "q"}, timeout_s=1))

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].get("code"), 0)
        self.assertEqual(events[0].get("data", {}).get("answer"), "hello")
        self.assertEqual(events[1].get("code"), -1)
        self.assertIn("upstream_stream_disconnected", str(events[1].get("message")))
        self.assertTrue(fake_resp.closed)

    def test_post_sse_plain_text_line_is_wrapped_as_answer(self):
        client = RagflowHttpClient(
            RagflowHttpClientConfig(base_url="http://127.0.0.1:9380", api_key="k", timeout_s=5.0)
        )
        fake_resp = _FakeSsePlainTextResponse()

        with patch("backend.services.ragflow_http_client.requests.post", return_value=fake_resp):
            events = list(client.post_sse("/api/v1/chats/c1/completions", body={"question": "q"}, timeout_s=1))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("code"), 0)
        self.assertEqual(events[0].get("data", {}).get("answer"), "hello from upstream")
        self.assertTrue(fake_resp.closed)

    def test_post_sse_choices_delta_is_wrapped_as_answer(self):
        client = RagflowHttpClient(
            RagflowHttpClientConfig(base_url="http://127.0.0.1:9380", api_key="k", timeout_s=5.0)
        )
        fake_resp = _FakeSseChoicesDeltaResponse()

        with patch("backend.services.ragflow_http_client.requests.post", return_value=fake_resp):
            events = list(client.post_sse("/api/v1/chats/c1/completions", body={"question": "q"}, timeout_s=1))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("code"), 0)
        self.assertEqual(events[0].get("data", {}).get("answer"), "delta token")
        self.assertTrue(fake_resp.closed)

    def test_post_sse_single_quote_dict_is_salvaged(self):
        client = RagflowHttpClient(
            RagflowHttpClientConfig(base_url="http://127.0.0.1:9380", api_key="k", timeout_s=5.0)
        )
        fake_resp = _FakeSseSingleQuoteDictResponse()

        with patch("backend.services.ragflow_http_client.requests.post", return_value=fake_resp):
            events = list(client.post_sse("/api/v1/chats/c1/completions", body={"question": "q"}, timeout_s=1))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("code"), 0)
        self.assertEqual(events[0].get("data", {}).get("answer"), "single-quote answer")
        self.assertTrue(fake_resp.closed)

    def test_post_sse_multiline_event_is_joined_by_sse_frame(self):
        client = RagflowHttpClient(
            RagflowHttpClientConfig(base_url="http://127.0.0.1:9380", api_key="k", timeout_s=5.0)
        )
        fake_resp = _FakeSseMultilineEventResponse()

        with patch("backend.services.ragflow_http_client.requests.post", return_value=fake_resp):
            events = list(client.post_sse("/api/v1/chats/c1/completions", body={"question": "q"}, timeout_s=1))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("code"), 0)
        self.assertEqual(events[0].get("data", {}).get("answer"), "multi-line answer")
        self.assertTrue(fake_resp.closed)

    def test_post_sse_flushes_trailing_event_without_blank_line(self):
        client = RagflowHttpClient(
            RagflowHttpClientConfig(base_url="http://127.0.0.1:9380", api_key="k", timeout_s=5.0)
        )
        fake_resp = _FakeSseNoBlankTerminatorResponse()

        with patch("backend.services.ragflow_http_client.requests.post", return_value=fake_resp):
            events = list(client.post_sse("/api/v1/chats/c1/completions", body={"question": "q"}, timeout_s=1))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("code"), 0)
        self.assertEqual(events[0].get("data", {}).get("answer"), "tail flush answer")
        self.assertTrue(fake_resp.closed)

    def test_post_sse_consecutive_data_lines_without_blank_are_emitted_incrementally(self):
        client = RagflowHttpClient(
            RagflowHttpClientConfig(base_url="http://127.0.0.1:9380", api_key="k", timeout_s=5.0)
        )
        fake_resp = _FakeSseConsecutiveDataNoBlankResponse()

        with patch("backend.services.ragflow_http_client.requests.post", return_value=fake_resp):
            events = list(client.post_sse("/api/v1/chats/c1/completions", body={"question": "q"}, timeout_s=1))

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].get("data", {}).get("answer"), "token-1")
        self.assertEqual(events[1].get("data", {}).get("answer"), "token-2")
        self.assertTrue(fake_resp.closed)


if __name__ == "__main__":
    unittest.main()
