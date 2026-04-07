"""Provider para consumir la API de Integralaia Visado."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import hashlib
import logging

import requests

logger = logging.getLogger(__name__)


@dataclass
class IntegralaiaProvider:
    base_url: str
    api_key: str
    timeout: int = 60
    extraction_timeout: int = 180
    use_doc_hash: bool = False

    @property
    def _headers(self) -> dict[str, str]:
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    @property
    def _headers_key_only(self) -> dict[str, str]:
        headers = {"accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _hash_params(self, doc_impoid: int | None) -> dict[str, str]:
        if not self.use_doc_hash or doc_impoid is None:
            return {}
        doc_text = str(doc_impoid)
        return {
            "doc_impoid": doc_text,
            "hash": hashlib.sha256(doc_text.encode("utf-8")).hexdigest(),
        }

    def create_operation(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/api/mw/operations",
            headers=self._headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def create_operation_from_middleware(self, payload: dict[str, Any]) -> dict[str, Any]:
        doc_impoid = payload.get("doc_impoid")
        request_payload = {"doc_impoid": str(doc_impoid)}
        response = requests.post(
            f"{self.base_url}/api/mw/create-operation-from-mdw",
            headers=self._headers,
            json=request_payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_document_types(self) -> list[dict[str, Any]]:
        response = requests.get(
            f"{self.base_url}/api/mw/document-types",
            headers=self._headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def configure_extraction_schema(self, document_code: str, schema: dict[str, Any]) -> dict[str, Any]:
        response = requests.put(
            f"{self.base_url}/api/mw/document-types/{document_code}/extraction-schema",
            headers=self._headers,
            json=schema,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def extract_sync_from_file(self, operation_id: str, file_path: str, document_type_code: str) -> dict[str, Any]:
        pdf = Path(file_path)
        if not pdf.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        with pdf.open("rb") as f:
            response = requests.post(
                f"{self.base_url}/api/mw/operations/{operation_id}/documents/extract-sync",
                headers=self._headers_key_only,
                files={"file": (pdf.name, f, "application/pdf")},
                data={"document_type_code": document_type_code},
                timeout=self.extraction_timeout,
            )

        if response.status_code == 422:
            detail = response.json().get("detail", {})
            raise ExtractionSchemaNotConfigured(
                document_type_code=document_type_code,
                message=detail.get("message", str(detail)),
            )

        response.raise_for_status()
        return response.json()

    def extract_sync_from_existing(
        self,
        operation_id: str,
        document_id: str,
        document_type_code: Optional[str] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"document_id": document_id}
        if document_type_code:
            payload["document_type_code"] = document_type_code

        response = requests.post(
            f"{self.base_url}/api/mw/operations/{operation_id}/documents/extract-sync",
            headers=self._headers,
            json=payload,
            timeout=self.extraction_timeout,
        )

        if response.status_code == 422:
            detail = response.json().get("detail", {})
            raise ExtractionSchemaNotConfigured(
                document_type_code=document_type_code or "unknown",
                message=detail.get("message", str(detail)),
            )

        response.raise_for_status()
        return response.json()

    def get_extracted_data(self, doc_impoid: int) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/api/mw/operations/{doc_impoid}/documents/extracted-data",
            headers=self._headers,
            params=self._hash_params(doc_impoid),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


class ExtractionSchemaNotConfigured(Exception):
    def __init__(self, document_type_code: str, message: str):
        self.document_type_code = document_type_code
        self.message = message
        super().__init__(message)
