from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = 'SEO NeuroAI'
    environment: str = 'development'
    database_url: str = 'postgresql+psycopg2://seo:seo@postgres:5432/seo_neuroai'
    redis_url: str = 'redis://redis:6379/0'
    secret_key: str = 'change-this-secret-in-production'
    openai_api_key: str = ''
    stripe_secret_key: str = ''
    stripe_webhook_secret: str = ''
    rate_limit_per_minute: int = 60

    class Config:
        env_file = '.env'


settings = Settings()
