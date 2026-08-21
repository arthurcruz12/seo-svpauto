import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import store
from backend.app.password_security import ensure_auth_version_column
from backend.app.security import pwd_context
from backend.app.server import app
from backend.app.work_traceability import list_work_cloud_files, tag_cloud_file


class CloudTrashTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = tempfile.NamedTemporaryFile(suffix="-cloud-trash.sqlite3", delete=False)
        cls.database.close()
        cls.storage = tempfile.TemporaryDirectory(prefix="seo-cloud-trash-")
        store.DATABASE_PATH = Path(cls.database.name)
        store.FILE_STORAGE_DIR = Path(cls.storage.name)
        store.ensure_company("SEO Trash Test")
        store.ensure_user(
            name="Administrador Trash",
            email="trash-admin@seo.local",
            role="admin",
            company_id="default-company",
            password_hash=pwd_context.hash("Seo-Trash-2026!"),
        )
        ensure_auth_version_column()
        cls.client = TestClient(app)
        first = cls.client.post(
            "/auth/login",
            json={"email": "trash-admin@seo.local", "password": "Seo-Trash-2026!"},
        )
        assert first.status_code == 200, first.text
        challenge = first.json()
        second = cls.client.post(
            "/auth/mfa",
            json={"challenge_id": challenge["challenge_id"], "code": challenge["development_code"]},
        )
        assert second.status_code == 200, second.text
        cls.headers = {"Authorization": f"Bearer {second.json()['access_token']}"}

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.storage.cleanup()
        Path(cls.database.name).unlink(missing_ok=True)

    def _save_file(self, name: str = "faturacao.xlsx") -> dict:
        return store.save_uploaded_file(
            "default-company",
            "trash-admin@seo.local",
            name,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "assistente-trabalho-resultado",
            b"PK\x03\x04trash-test-content",
        )

    def test_move_restore_and_permanent_delete(self):
        stored = self._save_file()
        file_id = stored["id"]
        local_path = store.FILE_STORAGE_DIR / "default-company" / f"{file_id}.bin"
        self.assertTrue(local_path.exists())

        active = self.client.get("/cloud/files", headers=self.headers)
        self.assertEqual(active.status_code, 200, active.text)
        self.assertIn(file_id, {item["id"] for item in active.json()})

        moved = self.client.post(f"/cloud/files/{file_id}/trash", headers=self.headers)
        self.assertEqual(moved.status_code, 200, moved.text)
        self.assertTrue(moved.json()["deletedAt"])

        active_after = self.client.get("/cloud/files", headers=self.headers)
        self.assertEqual(active_after.status_code, 200, active_after.text)
        self.assertNotIn(file_id, {item["id"] for item in active_after.json()})

        blocked_download = self.client.get(f"/cloud/files/{file_id}/download", headers=self.headers)
        self.assertEqual(blocked_download.status_code, 404)

        trash = self.client.get("/cloud/trash", headers=self.headers)
        self.assertEqual(trash.status_code, 200, trash.text)
        self.assertIn(file_id, {item["id"] for item in trash.json()})

        restored = self.client.post(f"/cloud/trash/{file_id}/restore", headers=self.headers)
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertIsNone(restored.json()["deletedAt"])

        active_restored = self.client.get("/cloud/files", headers=self.headers)
        self.assertIn(file_id, {item["id"] for item in active_restored.json()})

        self.assertEqual(self.client.post(f"/cloud/files/{file_id}/trash", headers=self.headers).status_code, 200)
        deleted = self.client.post(f"/cloud/trash/{file_id}/delete", headers=self.headers)
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertTrue(deleted.json()["deleted"])
        self.assertFalse(local_path.exists())
        self.assertNotIn(file_id, {item["id"] for item in self.client.get("/cloud/trash", headers=self.headers).json()})

    def test_work_traceability_excludes_trashed_file_but_restores_it(self):
        stored = self._save_file("Faturacao 20.08.xlsx")
        file_id = stored["id"]
        tag_cloud_file(
            company_id="default-company",
            file_id=file_id,
            origin="assistant-work-output",
            task_id="task-trash-20-08",
        )
        self.assertIn(file_id, {item["id"] for item in list_work_cloud_files("default-company")})

        moved = self.client.post(f"/cloud/files/{file_id}/trash", headers=self.headers)
        self.assertEqual(moved.status_code, 200, moved.text)
        self.assertNotIn(file_id, {item["id"] for item in list_work_cloud_files("default-company")})

        restored = self.client.post(f"/cloud/trash/{file_id}/restore", headers=self.headers)
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertIn(file_id, {item["id"] for item in list_work_cloud_files("default-company")})


if __name__ == "__main__":
    unittest.main()
