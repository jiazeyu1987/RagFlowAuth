import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from authx import TokenPayload
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import backend.app.modules.data_security.router as data_security_router_module
from backend.app.core.authz import AuthContext, admin_only, get_auth_context
from backend.database.schema.ensure import ensure_schema
from backend.services.egress_decision_audit_store import EgressDecisionAuditStore
from backend.services.egress_policy_store import EgressPolicyStore
from backend.services.system_feature_flag_store import (
    FLAG_EGRESS_POLICY_ENABLED,
    FLAG_PAPER_PLAG_ENABLED,
    FLAG_RESEARCH_UI_LAYOUT_ENABLED,
    SystemFeatureFlagStore as RuntimeSystemFeatureFlagStore,
)
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


class TestDataSecurityEgressRouterUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = make_temp_dir(prefix="ragflowauth_data_security_egress_router")
        self.db_path = os.path.join(str(self._tmp), "auth.db")
        ensure_schema(self.db_path)

        self.app = FastAPI()
        self.app.include_router(data_security_router_module.router, prefix="/api")
        self.app.dependency_overrides[admin_only] = lambda: TokenPayload(sub="admin_u1")
        self.app.dependency_overrides[get_auth_context] = lambda: AuthContext(
            deps=SimpleNamespace(kb_store=SimpleNamespace(db_path=self.db_path)),
            payload=TokenPayload(sub="u1"),
            user=SimpleNamespace(user_id="u1"),
            snapshot=SimpleNamespace(is_admin=True),
        )

        self._store_patcher = patch.object(
            data_security_router_module,
            "EgressPolicyStore",
            side_effect=lambda: EgressPolicyStore(db_path=self.db_path),
        )
        self._store_patcher.start()
        self._audit_store_patcher = patch.object(
            data_security_router_module,
            "EgressDecisionAuditStore",
            side_effect=lambda: EgressDecisionAuditStore(db_path=self.db_path),
        )
        self._audit_store_patcher.start()
        self._feature_store_patcher = patch.object(
            data_security_router_module,
            "SystemFeatureFlagStore",
            side_effect=lambda *args, **kwargs: RuntimeSystemFeatureFlagStore(db_path=self.db_path),
        )
        self._feature_store_patcher.start()

    def tearDown(self):
        self._feature_store_patcher.stop()
        self._audit_store_patcher.stop()
        self._store_patcher.stop()
        cleanup_dir(self._tmp)

    def test_get_egress_policy_config(self):
        with TestClient(self.app) as client:
            resp = client.get("/api/admin/security/egress/config")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["mode"], "intranet")
        self.assertIn("qwen-plus", payload["domestic_model_allowlist"])

    def test_update_egress_policy_config(self):
        with TestClient(self.app) as client:
            update_resp = client.put(
                "/api/admin/security/egress/config",
                json={
                    "mode": "extranet",
                    "domestic_model_allowlist": ["QWEN-PLUS", "glm-4-plus"],
                    "allowed_target_hosts": ["api.openai.com", "api.openai.com"],
                },
            )
            get_resp = client.get("/api/admin/security/egress/config")

        self.assertEqual(update_resp.status_code, 200)
        updated_payload = update_resp.json()
        self.assertEqual(updated_payload["mode"], "extranet")
        self.assertEqual(updated_payload["domestic_model_allowlist"], ["qwen-plus", "glm-4-plus"])
        self.assertEqual(updated_payload["allowed_target_hosts"], ["api.openai.com"])
        self.assertEqual(updated_payload["updated_by_user_id"], "admin_u1")

        self.assertEqual(get_resp.status_code, 200)
        persisted = get_resp.json()
        self.assertEqual(persisted["mode"], "extranet")

    def test_update_invalid_mode_returns_400(self):
        with TestClient(self.app) as client:
            resp = client.put("/api/admin/security/egress/config", json={"mode": "public"})

        self.assertEqual(resp.status_code, 400)

    def test_list_egress_audits(self):
        store = EgressDecisionAuditStore(db_path=self.db_path)
        store.log_decision(
            request_id="r1",
            actor_user_id="admin_u1",
            policy_mode="extranet",
            decision="block",
            hit_rules=[{"level": "high", "rule": "secret", "count": 1}],
            reason="egress_blocked_high_sensitive_payload",
            target_host="api.openai.com",
            target_model="qwen-plus",
            payload_level="high",
            request_meta={"operation": "POST"},
            created_at_ms=1000,
        )
        store.log_decision(
            request_id="r2",
            actor_user_id="admin_u1",
            policy_mode="extranet",
            decision="allow",
            hit_rules=[],
            reason=None,
            target_host="api.openai.com",
            target_model="qwen-plus",
            payload_level="low",
            request_meta={"operation": "GET"},
            created_at_ms=1100,
        )

        with TestClient(self.app) as client:
            resp = client.get("/api/admin/security/egress/audits?decision=block&limit=10")

        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(int(payload.get("total") or 0), 1)
        items = payload.get("items") or []
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get("request_id"), "r1")
        self.assertEqual(items[0].get("decision"), "block")

    def test_non_admin_is_forbidden(self):
        def _deny_admin():
            raise HTTPException(status_code=403, detail="admin_required")

        self.app.dependency_overrides[admin_only] = _deny_admin

        with TestClient(self.app) as client:
            resp = client.get("/api/admin/security/egress/config")
            audits_resp = client.get("/api/admin/security/egress/audits")

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(audits_resp.status_code, 403)

    def test_get_runtime_feature_flags(self):
        with TestClient(self.app) as client:
            resp = client.get("/api/security/feature-flags")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(bool(payload.get(FLAG_PAPER_PLAG_ENABLED)))
        self.assertTrue(bool(payload.get(FLAG_EGRESS_POLICY_ENABLED)))
        self.assertTrue(bool(payload.get(FLAG_RESEARCH_UI_LAYOUT_ENABLED)))

    def test_update_and_rollback_feature_flags(self):
        with TestClient(self.app) as client:
            update_resp = client.put(
                "/api/admin/security/feature-flags",
                json={FLAG_PAPER_PLAG_ENABLED: False},
            )
            rollback_resp = client.post("/api/admin/security/feature-flags/rollback-disable")

        self.assertEqual(update_resp.status_code, 200)
        self.assertFalse(bool(update_resp.json().get(FLAG_PAPER_PLAG_ENABLED)))

        self.assertEqual(rollback_resp.status_code, 200)
        rollback_payload = rollback_resp.json()
        self.assertFalse(bool(rollback_payload.get(FLAG_PAPER_PLAG_ENABLED)))
        self.assertFalse(bool(rollback_payload.get(FLAG_EGRESS_POLICY_ENABLED)))
        self.assertFalse(bool(rollback_payload.get(FLAG_RESEARCH_UI_LAYOUT_ENABLED)))

    def test_update_feature_flags_invalid_key_returns_400(self):
        with TestClient(self.app) as client:
            resp = client.put(
                "/api/admin/security/feature-flags",
                json={"unknown_feature": True},
            )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
