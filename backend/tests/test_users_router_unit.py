import unittest

from backend.app.modules.users.router import create_router, router


def _normalize_methods(route):
    return tuple(sorted(method for method in route.methods if method != "HEAD"))


class UsersRouterUnitTest(unittest.TestCase):
    def test_create_router_registers_expected_user_routes(self):
        users_router = create_router()
        route_map = {
            (route.path, _normalize_methods(route))
            for route in users_router.routes
            if hasattr(route, "methods")
        }

        self.assertEqual(
            route_map,
            {
                ("", ("GET",)),
                ("", ("POST",)),
                ("/{user_id}", ("DELETE",)),
                ("/{user_id}", ("GET",)),
                ("/{user_id}", ("PUT",)),
                ("/{user_id}/password", ("PUT",)),
            },
        )

    def test_module_router_uses_create_router_contract(self):
        self.assertEqual(len(router.routes), len(create_router().routes))

    def test_create_router_accepts_custom_registrars(self):
        calls = []

        def register_one(test_router):
            test_router.get("/one")(lambda: None)
            calls.append("one")

        def register_two(test_router):
            test_router.post("/two")(lambda: None)
            calls.append("two")

        users_router = create_router(registrars=(register_one, register_two))

        route_map = {
            (route.path, _normalize_methods(route))
            for route in users_router.routes
            if hasattr(route, "methods")
        }

        self.assertEqual(calls, ["one", "two"])
        self.assertEqual(
            route_map,
            {
                ("/one", ("GET",)),
                ("/two", ("POST",)),
            },
        )


if __name__ == "__main__":
    unittest.main()
