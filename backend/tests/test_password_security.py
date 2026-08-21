import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import store
from backend.app.password_security import ensure_auth_version_column
from backend.app.security import pwd_context
from backend.app.server import app


class PasswordSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = tempfile.NamedTemporaryFile(suffix="-password-security.sqlite3", delete=False)
        cls.database.close()
        store.DATABASE_PATH = Path(cls.database.name)
        store.ensure_company("SEO Empresa Teste")
        store.ensure_user(
            name="Administrador SEO",
            email="admin-security@seo.local",
            role="admin",
            company_id="default-company",
            password_hash=pwd_context.hash("Seo-Admin-2026"),
        )
        ensure_auth_version_column()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        Path(cls.database.name).unlink(missing_ok=True)

    @classmethod
    def login(cls, password: str):
        first = cls.client.post("/auth/login", json={"email": "admin-security@seo.local", "password": password})
        if first.status_code != 200:
            return first, None
        challenge = first.json()
        second = cls.client.post(
            "/auth/mfa",
            json={"challenge_id": challenge["challenge_id"], "code": challenge["development_code"]},
        )
        return first, second

    @staticmethod
    def auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_admin_password_change_requires_current_password_and_mfa(self):
        _, login = self.login("Seo-Admin-2026")
        self.assertIsNotNone(login)
        self.assertEqual(login.status_code, 200, login.text)
        old_token = login.json()["access_token"]

        rejected = self.client.post(
            "/auth/password/request",
            headers=self.auth(old_token),
            json={"current_password": "Wrong-Password-2026!"},
        )
        self.assertEqual(rejected.status_code, 401)

        requested = self.client.post(
            "/auth/password/request",
            headers=self.auth(old_token),
            json={"current_password": "Seo-Admin-2026"},
        )
        self.assertEqual(requested.status_code, 200, requested.text)
        challenge = requested.json()
        self.assertTrue(challenge["development_code"])

        changed = self.client.post(
            "/auth/password/confirm",
            headers=self.auth(old_token),
            json={
                "challenge_id": challenge["challenge_id"],
                "code": challenge["development_code"],
                "current_password": "Seo-Admin-2026",
                "new_password": "Novo-Admin-2026!",
                "confirm_password": "Novo-Admin-2026!",
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertTrue(changed.json()["reauthenticate"])

        self.assertEqual(self.client.get("/me", headers=self.auth(old_token)).status_code, 401)
        old_login, _ = self.login("Seo-Admin-2026")
        self.assertEqual(old_login.status_code, 401)
        new_login, new_mfa = self.login("Novo-Admin-2026!")
        self.assertEqual(new_login.status_code, 200, new_login.text)
        self.assertEqual(new_mfa.status_code, 200, new_mfa.text)


if __name__ == "__main__":
    unittest.main()
