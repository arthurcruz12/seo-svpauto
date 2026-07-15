from openai import OpenAI
from app.config import settings


class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    def generate_financial_insight(self, prompt: str) -> str:
        if self.client is None:
            return 'OpenAI service is not configured.'
        try:
            response = self.client.chat.completions.create(
                model='gpt-4.1-mini',
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are an enterprise financial AI assistant.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )

            return response.choices[0].message.content

        except Exception:
            return 'OpenAI service unavailable.'


openai_service = OpenAIService()
