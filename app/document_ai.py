class DocumentAI:
    def extract_financial_fields(self, raw_text: str) -> dict:
        return {
            'supplier': 'Detected Supplier',
            'amount': 120.0,
            'vat_amount': 27.6,
            'document_type': 'invoice',
            'confidence': 0.91,
            'engine': 'SEO DocumentAI'
        }


document_ai = DocumentAI()
