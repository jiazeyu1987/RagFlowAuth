import unittest

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from backend.app.core.config import DEFAULT_CORS_ORIGINS


class CorsConfigUnitTest(unittest.TestCase):
    def test_default_origins_cover_local_dev_ports(self):
        self.assertIn("http://localhost:3000", DEFAULT_CORS_ORIGINS)
        self.assertIn("http://127.0.0.1:3000", DEFAULT_CORS_ORIGINS)
        self.assertIn("http://localhost:3001", DEFAULT_CORS_ORIGINS)
        self.assertIn("http://127.0.0.1:3001", DEFAULT_CORS_ORIGINS)

    def test_preflight_allows_frontend_on_port_3001(self):
        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=DEFAULT_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.post("/api/auth/login")
        async def login():
            return {"ok": True}

        with TestClient(app) as client:
            response = client.options(
                "/api/auth/login",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3001")
