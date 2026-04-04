import os
import unittest
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core import authz as authz_module
from backend.app.modules.electronic_signature.router import router as electronic_signature_router
from backend.database.schema.ensure import ensure_schema
from backend.services.electronic_signature import (
    ElectronicSignatureError,
    ElectronicSignatureService,
    ElectronicSignatureStore,
)
from backend.services.users import hash_password
from backend.services.users.store import UserStore
from backend.tests._util_tempdir import cleanup_dir, make_temp_dir


SIGN_PASSWORD = "SignPass123"


class TestElectronicSignatureUnit(unittest.TestCase):
    def test_issue_consume_sign_and_verify(self):
        td = make_temp_dir(prefix="ragflowauth_esign_unit")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            user = SimpleNamespace(
                user_id="u-1",
                username="bob",
                password_hash=hash_password(SIGN_PASSWORD),
            )

            challenge = service.issue_challenge(user=user, password=SIGN_PASSWORD)
            self.assertIn("sign_token", challenge)
            self.assertGreater(challenge["expires_at_ms"], 0)

            signing_context = service.consume_sign_token(
                user=user,
                sign_token=challenge["sign_token"],
                action="document_approve",
            )
            signature = service.create_signature(
                signing_context=signing_context,
                user=user,
                record_type="knowledge_document_review",
                record_id="doc-1",
                action="document_approve",
                meaning="Document approval",
                reason="Approved after review",
                record_payload={"before": {"status": "pending"}, "after": {"status": "approved"}},
            )

            self.assertEqual(signature.record_id, "doc-1")
            self.assertTrue(service.verify_signature(signature_id=signature.signature_id))

            with self.assertRaises(ElectronicSignatureError) as ctx:
                service.consume_sign_token(
                    user=user,
                    sign_token=challenge["sign_token"],
                    action="document_approve",
                )
            self.assertEqual(ctx.exception.code, "sign_token_already_used")
        finally:
            cleanup_dir(td)

    def test_issue_challenge_rejects_wrong_password(self):
        td = make_temp_dir(prefix="ragflowauth_esign_password")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            user = SimpleNamespace(
                user_id="u-1",
                username="bob",
                password_hash=hash_password(SIGN_PASSWORD),
            )

            with self.assertRaises(ElectronicSignatureError) as ctx:
                service.issue_challenge(user=user, password="WrongPass123")
            self.assertEqual(ctx.exception.code, "signature_password_invalid")
        finally:
            cleanup_dir(td)

    def test_issue_challenge_rejects_inactive_or_disabled_user(self):
        td = make_temp_dir(prefix="ragflowauth_esign_disabled")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))

            inactive_user = SimpleNamespace(
                user_id="u-inactive",
                username="alice",
                password_hash=hash_password(SIGN_PASSWORD),
                status="inactive",
            )
            with self.assertRaises(ElectronicSignatureError) as inactive_ctx:
                service.issue_challenge(user=inactive_user, password=SIGN_PASSWORD)
            self.assertEqual(inactive_ctx.exception.code, "signature_user_inactive")

            disabled_user = SimpleNamespace(
                user_id="u-disabled",
                username="carol",
                password_hash=hash_password(SIGN_PASSWORD),
                status="active",
                disable_login_enabled=True,
                disable_login_until_ms=4_102_444_800_000,
            )
            with self.assertRaises(ElectronicSignatureError) as disabled_ctx:
                service.issue_challenge(user=disabled_user, password=SIGN_PASSWORD)
            self.assertEqual(disabled_ctx.exception.code, "signature_user_disabled")

            unauthorized_user = SimpleNamespace(
                user_id="u-unauthorized",
                username="dave",
                password_hash=hash_password(SIGN_PASSWORD),
                status="active",
                electronic_signature_enabled=False,
            )
            with self.assertRaises(ElectronicSignatureError) as unauthorized_ctx:
                service.issue_challenge(user=unauthorized_user, password=SIGN_PASSWORD)
            self.assertEqual(unauthorized_ctx.exception.code, "signature_user_not_authorized")
        finally:
            cleanup_dir(td)

    def test_consume_sign_token_rejects_user_disabled_after_issue(self):
        td = make_temp_dir(prefix="ragflowauth_esign_disable_after_issue")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            user = SimpleNamespace(
                user_id="u-1",
                username="bob",
                password_hash=hash_password(SIGN_PASSWORD),
                status="active",
                disable_login_enabled=False,
                disable_login_until_ms=None,
            )

            challenge = service.issue_challenge(user=user, password=SIGN_PASSWORD)
            user.disable_login_enabled = True
            user.disable_login_until_ms = 4_102_444_800_000

            with self.assertRaises(ElectronicSignatureError) as ctx:
                service.consume_sign_token(
                    user=user,
                    sign_token=challenge["sign_token"],
                    action="document_approve",
                )
            self.assertEqual(ctx.exception.code, "signature_user_disabled")
        finally:
            cleanup_dir(td)

    def test_signature_challenge_api_returns_short_lived_token(self):
        td = make_temp_dir(prefix="ragflowauth_esign_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            user = SimpleNamespace(
                user_id="u-1",
                username="bob",
                password_hash=hash_password(SIGN_PASSWORD),
            )
            deps = SimpleNamespace(
                electronic_signature_service=service,
                user_store=SimpleNamespace(db_path=db_path),
            )
            auth_ctx = SimpleNamespace(
                deps=deps,
                user=user,
                payload=SimpleNamespace(sub="u-1"),
                snapshot=None,
            )

            app = FastAPI()
            app.include_router(electronic_signature_router, prefix="/api")
            app.dependency_overrides[authz_module.get_auth_context] = lambda: auth_ctx

            with TestClient(app) as client:
                response = client.post("/api/electronic-signatures/challenge", json={"password": SIGN_PASSWORD})

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("sign_token", payload)
            self.assertGreater(int(payload["expires_at_ms"]), 0)
        finally:
            cleanup_dir(td)

    def test_management_api_returns_signature_and_verify_result(self):
        td = make_temp_dir(prefix="ragflowauth_esign_manage_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            user_store = UserStore(db_path=db_path)
            stored_user = user_store.create_user(
                username="bob",
                password=SIGN_PASSWORD,
                role="reviewer",
                full_name="Bob Zhang",
                electronic_signature_enabled=True,
            )
            user = SimpleNamespace(
                user_id=stored_user.user_id,
                username=stored_user.username,
                full_name=stored_user.full_name,
                password_hash=stored_user.password_hash,
                status=stored_user.status,
                electronic_signature_enabled=stored_user.electronic_signature_enabled,
            )
            challenge = service.issue_challenge(user=user, password=SIGN_PASSWORD)
            signing_context = service.consume_sign_token(
                user=user,
                sign_token=challenge["sign_token"],
                action="document_approve",
            )
            signature = service.create_signature(
                signing_context=signing_context,
                user=user,
                record_type="knowledge_document_review",
                record_id="doc-1",
                action="document_approve",
                meaning="Document approval",
                reason="Approved after review",
                record_payload={"before": {"status": "pending"}, "after": {"status": "approved"}},
            )

            deps = SimpleNamespace(
                electronic_signature_service=service,
                user_store=user_store,
            )
            auth_ctx = SimpleNamespace(
                deps=deps,
                user=user,
                payload=SimpleNamespace(sub="u-1"),
                snapshot=SimpleNamespace(is_admin=True),
            )

            app = FastAPI()
            app.include_router(electronic_signature_router, prefix="/api")
            app.dependency_overrides[authz_module.get_auth_context] = lambda: auth_ctx

            with TestClient(app) as client:
                list_response = client.get("/api/electronic-signatures")
                detail_response = client.get(f"/api/electronic-signatures/{signature.signature_id}")
                verify_response = client.post(f"/api/electronic-signatures/{signature.signature_id}/verify")

            self.assertEqual(list_response.status_code, 200)
            self.assertEqual(list_response.json()["items"][0]["signature_id"], signature.signature_id)
            self.assertTrue(list_response.json()["items"][0]["verified"])
            self.assertEqual(detail_response.status_code, 200)
            self.assertEqual(detail_response.json()["signature_id"], signature.signature_id)
            self.assertEqual(detail_response.json()["meaning"], "Document approval")
            self.assertEqual(detail_response.json()["signed_by_full_name"], "Bob Zhang")
            self.assertEqual(verify_response.status_code, 200)
            self.assertTrue(verify_response.json()["verified"])
        finally:
            cleanup_dir(td)

    def test_management_api_lists_and_updates_signature_authorization(self):
        td = make_temp_dir(prefix="ragflowauth_esign_authorization_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            user_store = UserStore(db_path=db_path)
            target_user = user_store.create_user(
                username="reviewer1",
                password=SIGN_PASSWORD,
                role="reviewer",
                electronic_signature_enabled=True,
            )
            admin_user = SimpleNamespace(
                user_id="admin-1",
                username="admin",
                password_hash=hash_password("AdminPass123"),
                status="active",
                electronic_signature_enabled=True,
            )

            deps = SimpleNamespace(
                electronic_signature_service=service,
                user_store=user_store,
            )
            auth_ctx = SimpleNamespace(
                deps=deps,
                user=admin_user,
                payload=SimpleNamespace(sub="admin-1"),
                snapshot=SimpleNamespace(is_admin=True),
            )

            app = FastAPI()
            app.include_router(electronic_signature_router, prefix="/api")
            app.dependency_overrides[authz_module.get_auth_context] = lambda: auth_ctx

            with TestClient(app) as client:
                list_response = client.get("/api/electronic-signature-authorizations")
                update_response = client.put(
                    f"/api/electronic-signature-authorizations/{target_user.user_id}",
                    json={"electronic_signature_enabled": False},
                )

            self.assertEqual(list_response.status_code, 200)
            items = list_response.json()["items"]
            self.assertTrue(any(item["user_id"] == target_user.user_id for item in items))
            self.assertEqual(update_response.status_code, 200)
            self.assertFalse(update_response.json()["electronic_signature_enabled"])

            updated_user = user_store.get_by_user_id(target_user.user_id)
            self.assertIsNotNone(updated_user)
            self.assertFalse(updated_user.electronic_signature_enabled)
        finally:
            cleanup_dir(td)

    def test_management_api_aggregates_tenant_signature_records_for_admin(self):
        td = make_temp_dir(prefix="ragflowauth_esign_manage_tenant_api")
        try:
            root_db_path = os.path.join(str(td), "auth.db")
            ensure_schema(root_db_path)
            tenant_db_path = os.path.join(str(td), "tenants", "company_2", "auth.db")
            ensure_schema(tenant_db_path)

            root_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=root_db_path))
            tenant_service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=tenant_db_path))
            tenant_user_store = UserStore(db_path=tenant_db_path)
            stored_tenant_user = tenant_user_store.create_user(
                username="wangxin",
                password=SIGN_PASSWORD,
                role="reviewer",
                full_name="王歆",
                electronic_signature_enabled=True,
            )

            tenant_user = SimpleNamespace(
                user_id=stored_tenant_user.user_id,
                username=stored_tenant_user.username,
                full_name=stored_tenant_user.full_name,
                password_hash=stored_tenant_user.password_hash,
                status=stored_tenant_user.status,
                electronic_signature_enabled=stored_tenant_user.electronic_signature_enabled,
            )
            tenant_challenge = tenant_service.issue_challenge(user=tenant_user, password=SIGN_PASSWORD)
            tenant_signing_context = tenant_service.consume_sign_token(
                user=tenant_user,
                sign_token=tenant_challenge["sign_token"],
                action="operation_approval_reject",
            )
            tenant_signature = tenant_service.create_signature(
                signing_context=tenant_signing_context,
                user=tenant_user,
                record_type="operation_approval_request",
                record_id="req-tenant-1",
                action="operation_approval_reject",
                meaning="Operation approval rejection",
                reason="Rejected during review",
                record_payload={"before": {"status": "in_approval"}, "after": {"status": "rejected"}},
            )

            admin_user = SimpleNamespace(
                user_id="admin-1",
                username="admin",
                password_hash=hash_password("AdminPass123"),
                status="active",
                electronic_signature_enabled=True,
            )
            deps = SimpleNamespace(
                electronic_signature_service=root_service,
                electronic_signature_store=root_service._store,
                user_store=UserStore(db_path=root_db_path),
            )
            auth_ctx = SimpleNamespace(
                deps=deps,
                user=admin_user,
                payload=SimpleNamespace(sub="admin-1"),
                snapshot=SimpleNamespace(is_admin=True),
            )

            app = FastAPI()
            app.include_router(electronic_signature_router, prefix="/api")
            app.dependency_overrides[authz_module.get_auth_context] = lambda: auth_ctx

            with TestClient(app) as client:
                list_response = client.get("/api/electronic-signatures?signed_by=wangxin")
                detail_response = client.get(f"/api/electronic-signatures/{tenant_signature.signature_id}")
                verify_response = client.post(f"/api/electronic-signatures/{tenant_signature.signature_id}/verify")

            self.assertEqual(list_response.status_code, 200)
            items = list_response.json()["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["signature_id"], tenant_signature.signature_id)
            self.assertEqual(items[0]["company_id"], 2)
            self.assertEqual(items[0]["signed_by_full_name"], "王歆")
            self.assertTrue(items[0]["verified"])

            self.assertEqual(detail_response.status_code, 200)
            self.assertEqual(detail_response.json()["signature_id"], tenant_signature.signature_id)
            self.assertEqual(detail_response.json()["company_id"], 2)
            self.assertEqual(detail_response.json()["signed_by_username"], "wangxin")
            self.assertEqual(detail_response.json()["signed_by_full_name"], "王歆")

            self.assertEqual(verify_response.status_code, 200)
            self.assertTrue(verify_response.json()["verified"])
            self.assertEqual(verify_response.json()["company_id"], 2)
        finally:
            cleanup_dir(td)

    def test_management_api_filters_signatures_by_signed_time_range(self):
        td = make_temp_dir(prefix="ragflowauth_esign_time_filter_api")
        try:
            db_path = os.path.join(str(td), "auth.db")
            ensure_schema(db_path)
            service = ElectronicSignatureService(store=ElectronicSignatureStore(db_path=db_path))
            user_store = UserStore(db_path=db_path)
            stored_user = user_store.create_user(
                username="reviewer1",
                password=SIGN_PASSWORD,
                role="reviewer",
                full_name="Reviewer One",
                electronic_signature_enabled=True,
            )
            user = SimpleNamespace(
                user_id=stored_user.user_id,
                username=stored_user.username,
                full_name=stored_user.full_name,
                password_hash=stored_user.password_hash,
                status=stored_user.status,
                electronic_signature_enabled=stored_user.electronic_signature_enabled,
            )

            challenge_a = service.issue_challenge(user=user, password=SIGN_PASSWORD)
            ctx_a = service.consume_sign_token(user=user, sign_token=challenge_a["sign_token"], action="document_approve")
            old_signature = service.create_signature(
                signing_context=ctx_a,
                user=user,
                record_type="knowledge_document_review",
                record_id="doc-old",
                action="document_approve",
                meaning="Approve old document",
                reason="Old record",
                record_payload={"doc": "old"},
            )

            challenge_b = service.issue_challenge(user=user, password=SIGN_PASSWORD)
            ctx_b = service.consume_sign_token(user=user, sign_token=challenge_b["sign_token"], action="document_reject")
            new_signature = service.create_signature(
                signing_context=ctx_b,
                user=user,
                record_type="knowledge_document_review",
                record_id="doc-new",
                action="document_reject",
                meaning="Reject new document",
                reason="New record",
                record_payload={"doc": "new"},
            )

            with service._store._conn() as conn:
                conn.execute(
                    "UPDATE electronic_signatures SET signed_at_ms = ? WHERE signature_id = ?",
                    (1_700_000_000_000, old_signature.signature_id),
                )
                conn.execute(
                    "UPDATE electronic_signatures SET signed_at_ms = ? WHERE signature_id = ?",
                    (1_800_000_000_000, new_signature.signature_id),
                )
                conn.commit()

            admin_user = SimpleNamespace(
                user_id="admin-1",
                username="admin",
                password_hash=hash_password("AdminPass123"),
                status="active",
                electronic_signature_enabled=True,
            )
            deps = SimpleNamespace(
                electronic_signature_service=service,
                electronic_signature_store=service._store,
                user_store=user_store,
            )
            auth_ctx = SimpleNamespace(
                deps=deps,
                user=admin_user,
                payload=SimpleNamespace(sub="admin-1"),
                snapshot=SimpleNamespace(is_admin=True),
            )

            app = FastAPI()
            app.include_router(electronic_signature_router, prefix="/api")
            app.dependency_overrides[authz_module.get_auth_context] = lambda: auth_ctx

            with TestClient(app) as client:
                response = client.get(
                    "/api/electronic-signatures",
                    params={
                        "signed_at_from_ms": 1_750_000_000_000,
                        "signed_at_to_ms": 1_850_000_000_000,
                    },
                )

            self.assertEqual(response.status_code, 200)
            items = response.json()["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["signature_id"], new_signature.signature_id)
            self.assertEqual(response.json()["total"], 1)
        finally:
            cleanup_dir(td)
