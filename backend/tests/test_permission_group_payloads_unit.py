import unittest

from backend.app.modules.permission_groups import payloads as permission_payloads


class _FakePayloadModel:
    def __init__(self, data, *, model_fields_set=None):
        self._data = dict(data)
        self.model_fields_set = set(model_fields_set or set())

    def model_dump(self):
        return dict(self._data)


class PermissionGroupPayloadsUnitTest(unittest.TestCase):
    def test_build_create_group_payload_adds_creator(self):
        payload = permission_payloads.build_create_group_payload(
            _FakePayloadModel({"name": "Ops", "description": "team"}),
            created_by="u-admin",
        )

        self.assertEqual(payload["created_by"], "u-admin")
        self.assertEqual(payload["name"], "Ops")
        self.assertEqual(payload["description"], "team")

    def test_build_update_group_payload_drops_none_values_by_default(self):
        payload = permission_payloads.build_update_group_payload(
            _FakePayloadModel(
                {"name": "Updated", "description": None},
                model_fields_set={"name", "description"},
            )
        )

        self.assertEqual(payload, {"name": "Updated"})

    def test_build_update_group_payload_keeps_explicit_folder_clear(self):
        payload = permission_payloads.build_update_group_payload(
            _FakePayloadModel(
                {"folder_id": None, "description": "Updated"},
                model_fields_set={"folder_id", "description"},
            )
        )

        self.assertEqual(payload, {"folder_id": None, "description": "Updated"})

    def test_merge_group_scope_payload_overrides_existing_values(self):
        merged = permission_payloads.merge_group_scope_payload(
            {"group_id": 7, "accessible_kbs": ["kb-a"], "folder_id": "folder-a"},
            {"accessible_kbs": ["kb-b"], "folder_id": None},
        )

        self.assertEqual(
            merged,
            {
                "group_id": 7,
                "accessible_kbs": ["kb-b"],
                "folder_id": None,
            },
        )


if __name__ == "__main__":
    unittest.main()
