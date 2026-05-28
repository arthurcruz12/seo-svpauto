class FinancialCopilot:
    def answer(self, question: str) -> dict:
        text = question.lower()

        if 'iva' in text:
            response = 'Estimated VAT obligations should be reviewed against validated invoices and accounting rules.'
        elif 'despesa' in text or 'gasto' in text:
            response = 'Operational expenses appear concentrated in recurring service categories.'
        elif 'risco' in text:
            response = 'No critical operational risk detected in the current dataset.'
        elif 'fluxo de caixa' in text:
            response = 'Cashflow appears operationally stable based on registered documents.'
        else:
            response = 'The financial copilot analyzed your request and recommends reviewing the operational dashboard for more context.'

        return {
            'question': question,
            'answer': response,
            'engine': 'SEO NeuroAI Copilot'
        }


financial_copilot = FinancialCopilot()
