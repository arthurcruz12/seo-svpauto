class DocumentAI:
    """Legacy text extraction facade.

    This module must never invent supplier, amount, VAT or confidence values.
    Real XLSX billing extraction is handled by app.agents.DocumentAgent. OCR/IDP
    text extraction remains NEEDS_REVIEW until a real extractor is configured.
    """

    def extract_financial_fields(self, raw_text: str) -> dict:
        return {
            "status": "NEEDS_REVIEW",
            "fields": {},
            "confidence": 0.0,
            "engine": "SEO DocumentAI",
            "reason": "real_text_extractor_not_configured",
            "has_input": bool(raw_text and raw_text.strip()),
        }


document_ai = DocumentAI()
