-- Additive SAF-T staging tables.
-- This migration intentionally does not alter financial_documents or any SNC tables.

CREATE TABLE IF NOT EXISTS saft_imports (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    filename VARCHAR NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    schema_version VARCHAR NULL,
    namespace VARCHAR NULL,
    status VARCHAR NOT NULL DEFAULT 'staged',
    source VARCHAR NOT NULL DEFAULT 'upload',
    company_tax_id VARCHAR NULL,
    source_company_name VARCHAR NULL,
    fiscal_year VARCHAR NULL,
    start_date VARCHAR NULL,
    end_date VARCHAR NULL,
    currency_code VARCHAR(3) NOT NULL DEFAULT 'EUR',
    validation_errors TEXT NULL,
    validation_warnings TEXT NULL,
    raw_file_reference VARCHAR NULL,
    created_by VARCHAR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_saft_import_tenant_company_sha256 UNIQUE (tenant_id, company_id, sha256)
);

CREATE INDEX IF NOT EXISTS ix_saft_imports_tenant_id ON saft_imports(tenant_id);
CREATE INDEX IF NOT EXISTS ix_saft_imports_company_id ON saft_imports(company_id);
CREATE INDEX IF NOT EXISTS ix_saft_imports_status ON saft_imports(status);
CREATE INDEX IF NOT EXISTS ix_saft_imports_sha256 ON saft_imports(sha256);

CREATE TABLE IF NOT EXISTS saft_staged_documents (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    saft_import_id INTEGER NOT NULL REFERENCES saft_imports(id),
    document_number VARCHAR NULL,
    document_type VARCHAR NOT NULL,
    document_status VARCHAR NULL,
    invoice_date DATE NULL,
    customer_id VARCHAR NULL,
    net_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    tax_payable NUMERIC(14,2) NOT NULL DEFAULT 0,
    gross_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    raw_gross_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    stage_status VARCHAR NOT NULL DEFAULT 'read_only',
    CONSTRAINT uq_saft_staged_import_document UNIQUE (saft_import_id, document_number)
);

CREATE INDEX IF NOT EXISTS ix_saft_staged_documents_tenant_id ON saft_staged_documents(tenant_id);
CREATE INDEX IF NOT EXISTS ix_saft_staged_documents_company_id ON saft_staged_documents(company_id);
CREATE INDEX IF NOT EXISTS ix_saft_staged_documents_import_id ON saft_staged_documents(saft_import_id);
CREATE INDEX IF NOT EXISTS ix_saft_staged_documents_number ON saft_staged_documents(document_number);

CREATE TABLE IF NOT EXISTS saft_anomalies (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    company_id INTEGER NOT NULL REFERENCES companies(id),
    saft_import_id INTEGER NOT NULL REFERENCES saft_imports(id),
    code VARCHAR NOT NULL,
    severity VARCHAR NOT NULL DEFAULT 'warning',
    document_number VARCHAR NULL,
    details TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_saft_anomalies_tenant_id ON saft_anomalies(tenant_id);
CREATE INDEX IF NOT EXISTS ix_saft_anomalies_company_id ON saft_anomalies(company_id);
CREATE INDEX IF NOT EXISTS ix_saft_anomalies_import_id ON saft_anomalies(saft_import_id);
CREATE INDEX IF NOT EXISTS ix_saft_anomalies_code ON saft_anomalies(code);
CREATE INDEX IF NOT EXISTS ix_saft_anomalies_severity ON saft_anomalies(severity);

-- Rollback, if needed, is isolated and reversible:
-- DROP TABLE IF EXISTS saft_anomalies;
-- DROP TABLE IF EXISTS saft_staged_documents;
-- DROP TABLE IF EXISTS saft_imports;
