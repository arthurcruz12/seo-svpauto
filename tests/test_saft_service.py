from decimal import Decimal

import pytest

from app.saft_service import normalize_saft, validate_saft_xml


VALID_SAFT = b'''<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:PT_1.04_01">
  <Header>
    <AuditFileVersion>1.04_01</AuditFileVersion>
    <CompanyID>SVP</CompanyID>
    <TaxRegistrationNumber>500000000</TaxRegistrationNumber>
    <CompanyName>SVP Auto</CompanyName>
    <FiscalYear>2026</FiscalYear>
    <StartDate>2026-01-01</StartDate>
    <EndDate>2026-12-31</EndDate>
    <CurrencyCode>EUR</CurrencyCode>
  </Header>
  <SourceDocuments>
    <SalesInvoices>
      <Invoice>
        <InvoiceNo>FT 2026/1</InvoiceNo>
        <InvoiceStatus>N</InvoiceStatus>
        <InvoiceDate>2026-08-19</InvoiceDate>
        <InvoiceType>FT</InvoiceType>
        <CustomerID>C1</CustomerID>
        <DocumentTotals>
          <TaxPayable>23.00</TaxPayable>
          <NetTotal>100.00</NetTotal>
          <GrossTotal>123.00</GrossTotal>
        </DocumentTotals>
      </Invoice>
      <Invoice>
        <InvoiceNo>NC 2026/1</InvoiceNo>
        <InvoiceStatus>N</InvoiceStatus>
        <InvoiceDate>2026-08-19</InvoiceDate>
        <InvoiceType>NC</InvoiceType>
        <CustomerID>C1</CustomerID>
        <DocumentTotals>
          <TaxPayable>23.00</TaxPayable>
          <NetTotal>100.00</NetTotal>
          <GrossTotal>123.00</GrossTotal>
        </DocumentTotals>
      </Invoice>
    </SalesInvoices>
  </SourceDocuments>
</AuditFile>'''


def test_valid_saft_is_structurally_accepted():
    _root, validation = validate_saft_xml(VALID_SAFT)
    assert validation.valid is True
    assert validation.schema_version == "1.04_01"
    assert validation.namespace == "urn:OECD:StandardAuditFile-Tax:PT_1.04_01"


def test_credit_note_is_normalized_to_negative_values_without_mutating_source():
    result = normalize_saft(VALID_SAFT)
    assert result["counts"]["documents"] == 2
    credit_note = next(item for item in result["documents"] if item["document_type"] == "NC")
    assert credit_note["net_total"] == Decimal("-100.00")
    assert credit_note["tax_payable"] == Decimal("-23.00")
    assert credit_note["gross_total"] == Decimal("-123.00")
    assert credit_note["raw_gross_total"] == Decimal("123.00")


def test_duplicate_document_number_is_reported_as_anomaly():
    duplicated = VALID_SAFT.replace(b"NC 2026/1", b"FT 2026/1")
    result = normalize_saft(duplicated)
    assert any(item["code"] == "DUPLICATE_DOCUMENT_NUMBER" for item in result["anomalies"])


def test_total_mismatch_is_reported():
    broken = VALID_SAFT.replace(b"<GrossTotal>123.00</GrossTotal>", b"<GrossTotal>999.00</GrossTotal>", 1)
    result = normalize_saft(broken)
    assert any(item["code"] == "TOTAL_MISMATCH" for item in result["anomalies"])


def test_dtd_is_rejected_before_parsing():
    payload = b'''<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><AuditFile>&xxe;</AuditFile>'''
    with pytest.raises(ValueError, match="DTD"):
        normalize_saft(payload)
