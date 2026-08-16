from scripts.smoke_critical_path import assert_admin_status_body


def test_assert_admin_status_body_minimal_valid():
    body = {
        "redis_ok": True,
        "canary": {},
        "jobs": [],
        "providers": {
            "providers": ["mobile_de"],
            "default_import_cost_profile": "DEFAULT",
        },
    }
    assert_admin_status_body(body)  # no raise


def test_assert_admin_status_body_missing_providers():
    body = {"redis_ok": True, "canary": {}, "jobs": []}
    with _expect_assert("providers"):
        assert_admin_status_body(body)


def test_assert_admin_status_body_providers_not_dict():
    body = {
        "redis_ok": True,
        "canary": {},
        "jobs": [],
        "providers": ["not_a_dict"],
    }
    with _expect_assert("no es objeto"):
        assert_admin_status_body(body)


def test_assert_admin_status_body_providers_list_not_list():
    body = {
        "redis_ok": True,
        "canary": {},
        "jobs": [],
        "providers": {"providers": "not_a_list"},
    }
    with _expect_assert("no es lista"):
        assert_admin_status_body(body)


def test_assert_admin_status_body_registered_none_ok():
    body = {
        "redis_ok": True,
        "canary": {},
        "jobs": [],
        "providers": {"default_import_cost_profile": "ES"},
    }
    assert_admin_status_body(body)  # registered=None is fine


class _expect_assert:
    def __init__(self, fragment: str):
        self.fragment = fragment

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not AssertionError:
            return False
        msg = str(exc_val)
        assert self.fragment in msg, f"Expected '{self.fragment}' in '{msg}'"
        return True  # suppress
