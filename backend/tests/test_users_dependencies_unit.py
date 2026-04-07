import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.app.modules.users import dependencies as user_dependencies


class UsersDependenciesUnitTest(unittest.TestCase):
    def test_get_user_store_returns_global_user_store(self):
        user_store = object()

        self.assertIs(
            user_dependencies.get_user_store(SimpleNamespace(user_store=user_store)),
            user_store,
        )

    def test_get_scoped_permission_group_store_returns_store_or_none(self):
        store = object()

        self.assertIs(
            user_dependencies.get_scoped_permission_group_store(
                SimpleNamespace(permission_group_store=store)
            ),
            store,
        )
        self.assertIsNone(user_dependencies.get_scoped_permission_group_store(SimpleNamespace()))

    def test_build_users_repo_passes_global_deps_and_permission_group_store(self):
        global_deps = object()
        permission_group_store = object()

        with patch.object(user_dependencies, "UsersRepo", return_value="repo") as users_repo:
            result = user_dependencies.build_users_repo(
                global_deps=global_deps,
                permission_group_store=permission_group_store,
            )

        users_repo.assert_called_once_with(
            global_deps,
            permission_group_store=permission_group_store,
        )
        self.assertEqual(result, "repo")

    def test_build_users_service_wraps_repo(self):
        global_deps = object()
        permission_group_store = object()

        with patch.object(user_dependencies, "build_users_repo", return_value="repo") as build_repo, patch.object(
            user_dependencies,
            "UsersService",
            return_value="service",
        ) as users_service:
            result = user_dependencies.build_users_service(
                global_deps=global_deps,
                permission_group_store=permission_group_store,
            )

        build_repo.assert_called_once_with(
            global_deps=global_deps,
            permission_group_store=permission_group_store,
        )
        users_service.assert_called_once_with("repo")
        self.assertEqual(result, "service")

    def test_get_service_threads_scoped_permission_group_store_into_service_builder(self):
        global_deps = object()
        scoped_deps = SimpleNamespace(permission_group_store="store")

        with patch.object(
            user_dependencies,
            "build_users_service",
            return_value="service",
        ) as build_service:
            result = user_dependencies.get_service(
                global_deps=global_deps,
                scoped_deps=scoped_deps,
            )

        build_service.assert_called_once_with(
            global_deps=global_deps,
            permission_group_store="store",
        )
        self.assertEqual(result, "service")


if __name__ == "__main__":
    unittest.main()
