import sys
import unittest
from pathlib import Path

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import CurrentUser, extract_roles, require_roles


class AuthRoleTests(unittest.TestCase):
    def test_extract_roles_collects_realm_and_client_roles(self) -> None:
        claims = {
            "realm_access": {"roles": ["Applicant"]},
            "resource_access": {"ektrm-web": {"roles": ["OPS"]}},
        }
        roles = extract_roles(claims, "ektrm-web")
        self.assertEqual(roles, frozenset({"Applicant", "OPS"}))

    def test_require_roles_allows_expected_role(self) -> None:
        user = CurrentUser(
            subject="user-1",
            username="applicant.demo",
            email="applicant@example.local",
            roles=frozenset({"Applicant"}),
            claims={},
        )
        dependency = require_roles("Applicant")
        result = dependency(user)
        self.assertEqual(result.subject, "user-1")

    def test_require_roles_blocks_forbidden_role(self) -> None:
        user = CurrentUser(
            subject="user-2",
            username="applicant.demo",
            email="applicant@example.local",
            roles=frozenset({"Applicant"}),
            claims={},
        )
        dependency = require_roles("OPS")
        with self.assertRaises(HTTPException) as context:
            dependency(user)
        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
