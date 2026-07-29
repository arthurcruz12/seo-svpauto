# Produção Azure

## Recursos necessários

- Azure Container Apps para a API.
- Azure Static Web Apps para o frontend.
- Azure Blob Storage para documentos e backups.
- OCR local (RapidOCR) dentro da API; Azure Document Intelligence não é necessário.
- Azure Key Vault para chaves OpenAI, JWT e Storage.
- Application Insights para métricas, erros e alertas.

## Variáveis obrigatórias

Copiar `backend/.env.example` para o gestor de segredos do ambiente. Nunca publicar o ficheiro `.env`.

## Segurança

- HTTPS obrigatório.
- Restringir CORS ao domínio final.
- MFA obrigatório para administradores.
- Backups diários, retenção definida e teste mensal de recuperação.
- Alertas para erros 5xx, latência elevada e falhas de OCR/IA.

## Publicação

1. Criar os recursos com Azure Developer CLI.
2. Guardar segredos no Key Vault.
3. Configurar domínio e certificado gerido.
4. Executar testes de integração e carga.
5. Validar recuperação a partir de um backup antes da entrada em produção.
