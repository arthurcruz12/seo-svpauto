FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# app.main_saft imports the existing app.main:app and only adds isolated SAF-T
# routes. SAF-T writes remain disabled unless SAFT_INTEGRATION_ENABLED=true.
CMD ["uvicorn", "app.main_saft:app", "--host", "0.0.0.0", "--port", "8000"]
