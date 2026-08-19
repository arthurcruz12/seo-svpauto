from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.etree import ElementTree as ET


@dataclass(frozen=True)
class SaftValidationResult:
    valid: bool
    schema_version: str | None
    namespace: str | None
    warnings: list[str]
    errors: list[str]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _namespace(tag: str) -> str | None:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return None


def _first_text(node: ET.Element, name: str) -> str | None:
    for child in node.iter():
        if _local_name(child.tag) == name:
            text = (child.text or "").strip()
            return text or None
    return None


def _decimal(value: str | None) -> Decimal:
    if not value:
        return Decimal("0.00")
    try:
        return Decimal(value.replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def validate_saft_xml(payload: bytes) -> tuple[ET.Element, SaftValidationResult]:
    errors: list[str] = []
    warnings: list[str] = []

    if not payload.strip():
        raise ValueError("Empty SAF-T file")
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("DTD and external entities are not allowed")

    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    if _local_name(root.tag) != "AuditFile":
        errors.append("Root element must be AuditFile")

    namespace = _namespace(root.tag)
    schema_version = _first_text(root, "AuditFileVersion")
    if not schema_version:
        warnings.append("AuditFileVersion was not found")

    required_header_fields = ("CompanyID", "TaxRegistrationNumber", "CompanyName", "FiscalYear", "StartDate", "EndDate")
    for field in required_header_fields:
        if not _first_text(root, field):
            errors.append(f"Missing required header field: {field}")

    return root, SaftValidationResult(
        valid=not errors,
        schema_version=schema_version,
        namespace=namespace,
        warnings=warnings,
        errors=errors,
    )


def normalize_saft(payload: bytes) -> dict[str, Any]:
    root, validation = validate_saft_xml(payload)

    header = {
        "company_id": _first_text(root, "CompanyID"),
        "tax_registration_number": _first_text(root, "TaxRegistrationNumber"),
        "company_name": _first_text(root, "CompanyName"),
        "fiscal_year": _first_text(root, "FiscalYear"),
        "start_date": _first_text(root, "StartDate"),
        "end_date": _first_text(root, "EndDate"),
        "currency_code": _first_text(root, "CurrencyCode") or "EUR",
        "audit_file_version": validation.schema_version,
        "namespace": validation.namespace,
    }

    customers: list[dict[str, Any]] = []
    suppliers: list[dict[str, Any]] = []
    products: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []

    for node in root.iter():
        name = _local_name(node.tag)
        if name == "Customer":
            customers.append({
                "customer_id": _first_text(node, "CustomerID"),
                "tax_id": _first_text(node, "CustomerTaxID"),
                "name": _first_text(node, "CompanyName"),
                "account_id": _first_text(node, "AccountID"),
            })
        elif name == "Supplier":
            suppliers.append({
                "supplier_id": _first_text(node, "SupplierID"),
                "tax_id": _first_text(node, "SupplierTaxID"),
                "name": _first_text(node, "CompanyName"),
                "account_id": _first_text(node, "AccountID"),
            })
        elif name == "Product":
            products.append({
                "product_code": _first_text(node, "ProductCode"),
                "product_group": _first_text(node, "ProductGroup"),
                "description": _first_text(node, "ProductDescription"),
                "product_number_code": _first_text(node, "ProductNumberCode"),
            })
        elif name == "Invoice":
            gross_total = _decimal(_first_text(node, "GrossTotal"))
            net_total = _decimal(_first_text(node, "NetTotal"))
            tax_payable = _decimal(_first_text(node, "TaxPayable"))
            invoice_type = _first_text(node, "InvoiceType") or "UNKNOWN"
            is_credit_note = invoice_type.upper() in {"NC", "CN"}
            sign = Decimal("-1") if is_credit_note else Decimal("1")
            documents.append({
                "document_number": _first_text(node, "InvoiceNo"),
                "document_type": invoice_type,
                "document_status": _first_text(node, "InvoiceStatus"),
                "invoice_date": _date(_first_text(node, "InvoiceDate")),
                "customer_id": _first_text(node, "CustomerID"),
                "net_total": sign * abs(net_total),
                "tax_payable": sign * abs(tax_payable),
                "gross_total": sign * abs(gross_total),
                "raw_gross_total": gross_total,
            })

    anomalies: list[dict[str, Any]] = []
    seen_numbers: set[str] = set()
    for document in documents:
        number = document["document_number"]
        if not number:
            anomalies.append({"code": "MISSING_DOCUMENT_NUMBER", "severity": "high", "document": None})
        elif number in seen_numbers:
            anomalies.append({"code": "DUPLICATE_DOCUMENT_NUMBER", "severity": "high", "document": number})
        else:
            seen_numbers.add(number)

        expected = document["net_total"] + document["tax_payable"]
        if abs(expected - document["gross_total"]) > Decimal("0.02"):
            anomalies.append({
                "code": "TOTAL_MISMATCH",
                "severity": "high",
                "document": number,
                "expected_total": str(expected),
                "gross_total": str(document["gross_total"]),
            })

    return {
        "sha256": sha256_bytes(payload),
        "validation": {
            "valid": validation.valid,
            "schema_version": validation.schema_version,
            "namespace": validation.namespace,
            "warnings": validation.warnings,
            "errors": validation.errors,
        },
        "header": header,
        "counts": {
            "customers": len(customers),
            "suppliers": len(suppliers),
            "products": len(products),
            "documents": len(documents),
            "anomalies": len(anomalies),
        },
        "customers": customers,
        "suppliers": suppliers,
        "products": products,
        "documents": documents,
        "anomalies": anomalies,
    }
