from __future__ import annotations

import os


def upload_document(company_id: str, file_id: str, filename: str, content: bytes, content_type: str) -> str | None:
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    if not connection_string:
        return None
    try:
        from azure.storage.blob import BlobServiceClient, ContentSettings

        container_name = os.getenv("AZURE_STORAGE_CONTAINER", "seo-documentos")
        service = BlobServiceClient.from_connection_string(connection_string)
        container = service.get_container_client(container_name)
        try:
            container.create_container()
        except Exception:
            pass
        blob_name = f"{company_id}/{file_id}/{filename}"
        container.upload_blob(blob_name, content, overwrite=True, content_settings=ContentSettings(content_type=content_type))
        return blob_name
    except Exception:
        return None
