from __future__ import annotations

import os
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from uuid import UUID


class ArtifactStorage(ABC):
    provider = "abstract"

    @abstractmethod
    def save(self, *, tenant_id: int, artifact_id: str, filename: str, content: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def open(self, storage_reference: str) -> BinaryIO:
        raise NotImplementedError

    @abstractmethod
    def exists(self, storage_reference: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_reference: str) -> None:
        raise NotImplementedError


class LocalPersistentStorage(ArtifactStorage):
    provider = "local"

    def __init__(self, root: str | Path | None = None) -> None:
        configured = root or os.getenv("SEO_ARTIFACT_STORAGE_PATH", "data/agent-storage")
        self.root = Path(configured).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = Path(filename or "artifact.bin").name
        return name[:180] or "artifact.bin"

    def _resolve_reference(self, storage_reference: str) -> Path:
        candidate = (self.root / storage_reference).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("invalid storage reference") from exc
        return candidate

    def save(self, *, tenant_id: int, artifact_id: str, filename: str, content: bytes) -> str:
        UUID(artifact_id)
        safe_name = self._safe_filename(filename)
        relative = Path(f"tenant-{tenant_id}") / artifact_id / safe_name
        target = self._resolve_reference(str(relative))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return relative.as_posix()

    def open(self, storage_reference: str) -> BinaryIO:
        target = self._resolve_reference(storage_reference)
        return target.open("rb")

    def exists(self, storage_reference: str) -> bool:
        return self._resolve_reference(storage_reference).is_file()

    def delete(self, storage_reference: str) -> None:
        target = self._resolve_reference(storage_reference)
        if target.exists():
            target.unlink()


class MemoryArtifactStorage(ArtifactStorage):
    """Test storage with the same opaque-reference contract as persistent providers."""

    provider = "memory"

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def save(self, *, tenant_id: int, artifact_id: str, filename: str, content: bytes) -> str:
        UUID(artifact_id)
        reference = f"tenant-{tenant_id}/{artifact_id}/{Path(filename).name}"
        self._objects[reference] = bytes(content)
        return reference

    def open(self, storage_reference: str) -> BinaryIO:
        if storage_reference not in self._objects:
            raise FileNotFoundError(storage_reference)
        return BytesIO(self._objects[storage_reference])

    def exists(self, storage_reference: str) -> bool:
        return storage_reference in self._objects

    def delete(self, storage_reference: str) -> None:
        self._objects.pop(storage_reference, None)


def get_artifact_storage() -> ArtifactStorage:
    provider = os.getenv("SEO_ARTIFACT_STORAGE_PROVIDER", "local").strip().lower()
    if provider == "local":
        return LocalPersistentStorage()
    raise RuntimeError(f"Unsupported artifact storage provider: {provider}")
