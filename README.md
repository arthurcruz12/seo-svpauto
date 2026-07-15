# SEO — Sistema de Eficiência Operacional com IA

Backend MVP funcional para o aplicativo **SEO — Sistema de Eficiência Operacional**, um SaaS mobile/empresarial focado em automação contabilística, financeira e administrativa com IA.

## Arquitetura oficial do backend

O backend oficial do projeto está exclusivamente na pasta:

```text
app/
```

O ponto de entrada oficial da API é:

```bash
app.main:app
```

Todas as importações internas devem usar:

```python
from app.nome_do_modulo import ...
```

A estrutura antiga `backend/app` foi descontinuada e não deve ser usada em CI, Docker, testes ou deploy.

## Objetivo

O SEO funciona como um AI Backoffice para empresas: interpreta documentos, classifica despesas, gera alertas, mantém logs de auditoria e prepara dados para controlo financeiro e contabilístico.

## Funcionalidades deste MVP

- API FastAPI funcional
- Registo de empresas
- Registo de documentos financeiros
- Classificação automática de despesas
- Dashboard financeiro básico
- Logs de auditoria
- Estrutura preparada para OCR real, IA e integrações bancárias

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- SQLite no MVP
- Pydantic
- Uvicorn
- Pytest
- Docker
- Alembic

## Como correr localmente

```bash
python -m venv .venv
```

### Windows PowerShell

```bash
.venv\Scripts\Activate.ps1
```

### Instalar dependências

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Iniciar a API

```bash
python -m uvicorn app.main:app --reload
```

### Executar testes

```bash
python -m pytest -q
```

### Docker

```bash
docker compose up --build
```

## Endpoints principais

### Health check
GET /health

### Criar empresa
POST /companies

### Criar documento financeiro
POST /documents

### Processar documento
POST /documents/{document_id}/process

### Dashboard
GET /dashboard/{company_id}

### Logs
GET /audit-logs

## Compliance

Toda automação deve ser:

- rastreável
- auditável
- reversível
- documentada
- compatível com auditorias

## Roadmap

- API versionada em `/api/v1`
- JWT Authentication
- OCR real
- IA financeira
- Integrações bancárias
- Dashboard mobile
- Compliance engine
- Chat IA empresarial

---

# Função da Inteligência Artificial do SEO

A Inteligência Artificial (IA) do Sistema de Eficiência Operacional (SEO) é o núcleo responsável por automatizar, interpretar, validar e transformar dados empresariais em informações estratégicas para apoio à gestão, contabilidade e tomada de decisão.

A sua principal função é eliminar tarefas manuais e repetitivas, reduzindo erros operacionais, aumentando a produtividade e fornecendo informações confiáveis em tempo real.

A IA atua como um assistente inteligente capaz de compreender documentos, analisar bases de dados, interpretar informações financeiras, contabilísticas e operacionais, identificar inconsistências e sugerir ações corretivas, sempre mantendo total rastreabilidade das decisões tomadas.

## Princípios obrigatórios de funcionamento

Toda ação da IA deve ser rastreável, auditável, explicável, reversível e sujeita a validação humana quando o nível de confiança for insuficiente ou existir impacto contabilístico, fiscal ou financeiro relevante.

O processamento deve respeitar o RGPD/GDPR, a legislação contabilística e fiscal portuguesa aplicável, as regras da Autoridade Tributária e Aduaneira, os requisitos de segurança de dados e as normas de compliance empresarial da União Europeia.

## Principais responsabilidades

### 1. Leitura Inteligente de Documentos

A IA analisa automaticamente documentos em diversos formatos, como PDF, imagens, fotografias, Excel, CSV, XML e SAF-T, utilizando tecnologias de reconhecimento ótico de caracteres (OCR) e processamento inteligente de documentos (IDP).

Entre os documentos suportados estão:

- Faturas
- Faturas-recibo
- Notas de crédito
- Notas de débito
- Recibos
- Guias de transporte
- Extratos bancários
- Documentos de marketplaces, incluindo OVOKO e Recambio Verde

Após a leitura, a IA extrai e estrutura automaticamente todas as informações relevantes para utilização pelo sistema, incluindo fornecedor ou cliente, NIF, número do documento, datas de emissão e vencimento, moeda, valores sem IVA, IVA, total, estado e forma de pagamento.

### 2. Classificação Automática

Cada documento é identificado e classificado automaticamente, distinguindo o seu tipo, origem, fornecedor, cliente, estado financeiro, forma de pagamento e categoria contabilística.

O sistema identifica automaticamente, por exemplo:

- Faturas
- Faturas-recibo
- Notas de crédito
- Documentos pagos
- Documentos pendentes
- Documentos vencidos
- Débitos diretos
- Transferências bancárias
- Faturas a pagar e respetiva data de vencimento

### 3. Validação Contabilística

A IA realiza verificações automáticas para garantir a consistência dos documentos.

São efetuadas validações como:

- Conferência dos cálculos de IVA
- Verificação da soma entre valor sem IVA, IVA e valor total
- Identificação de documentos duplicados
- Verificação de datas inválidas
- Validação de NIF, IBAN e referências de pagamento
- Identificação de inconsistências contabilísticas
- Validação do sinal contabilístico conforme o tipo de documento

Sempre que necessário, são emitidos alertas para revisão humana. A IA nunca deve ocultar incertezas: cada extração e classificação deve conservar o nível de confiança, a origem do dado e o histórico de correções.

### 4. Automação Financeira

A IA acompanha o ciclo financeiro dos documentos, identificando:

- Documentos pagos
- Documentos por liquidar
- Faturas vencidas
- Pagamentos por débito direto
- Transferências bancárias
- Prioridades de pagamento
- Datas de vencimento e dias em atraso

Com base nessas informações, auxilia a equipa financeira na organização das obrigações da empresa, sem executar pagamentos ou lançamentos irreversíveis sem as permissões e validações definidas.

### 5. Processamento Inteligente de Excel

Ao importar ficheiros Excel, a IA interpreta automaticamente a estrutura da folha de cálculo, identifica os diferentes tipos de documentos e organiza os dados de forma padronizada.

Os registos devem ser separados, no mínimo, em:

- Faturas
- Faturas-recibo
- Notas de crédito

A IA calcula automaticamente:

- Valor sem IVA
- Valor do IVA
- Valor total
- Totais por fornecedor
- Totais por período
- Totais por tipo de documento

As notas de crédito são sempre tratadas contabilisticamente como valores negativos, independentemente da forma como estejam registadas no ficheiro de origem. O sistema deve preservar simultaneamente o valor original importado e o valor normalizado para garantir rastreabilidade e auditoria.

### 6. Apoio à Contabilidade

A IA organiza e prepara as informações para facilitar o trabalho contabilístico, reduzindo significativamente o tempo gasto com conferências manuais.

O sistema fornece dados consistentes para:

- Reconciliações
- Conferências contabilísticas
- Preparação de documentos
- Auditorias
- Fechos mensais
- Controlo financeiro

A IA apoia o profissional responsável, mas não substitui a validação contabilística ou fiscal legalmente exigida.

### 7. Business Intelligence

A IA transforma dados operacionais em indicadores estratégicos.

Entre os indicadores gerados encontram-se:

- Total faturado
- Total por fornecedor
- Total de IVA
- Total líquido
- Documentos pendentes
- Documentos vencidos
- Evolução mensal
- Tendências financeiras
- Indicadores de desempenho (KPIs)

Estas informações são apresentadas em dashboards interativos para apoiar a tomada de decisão, com possibilidade de rastrear cada indicador até aos documentos que lhe deram origem.

### 8. Deteção de Anomalias

A IA monitoriza continuamente os dados da empresa para identificar situações que merecem atenção.

Exemplos:

- Valores fora do padrão
- Documentos duplicados
- Pagamentos em atraso
- Erros de lançamento
- Inconsistências fiscais
- Divergências entre documentos e registos internos

Sempre que uma anomalia é detetada, o sistema gera um alerta detalhado, informa a regra ou evidência que originou o alerta e apresenta uma explicação clara para facilitar a correção.

### 9. Aprendizagem Contínua

A IA aprende com as correções efetuadas pelos utilizadores autorizados e com o histórico de documentos processados, melhorando progressivamente a sua capacidade de classificação, extração de dados e identificação de padrões.

Este processo deve ser controlado, versionado e auditável. As correções não podem alterar silenciosamente documentos anteriores nem propagar regras sem validação. O objetivo é aumentar continuamente a precisão das análises e reduzir a necessidade de intervenção humana, mantendo supervisão adequada.

### 10. Assistente Inteligente para Gestão

Além do processamento documental, a IA funciona como um assistente virtual para gestores e colaboradores.

Os utilizadores podem realizar perguntas em linguagem natural, tais como:

- “Quais faturas vencem esta semana?”
- “Quanto temos a pagar ao fornecedor X?”
- “Mostre todas as notas de crédito do último trimestre.”
- “Qual foi o IVA pago no mês passado?”
- “Quais documentos apresentam inconsistências?”
- “Qual fornecedor representa o maior custo este mês?”

A IA interpreta a pergunta, respeita as permissões do utilizador, consulta os dados do sistema e responde de forma rápida, precisa, contextualizada e acompanhada das fontes internas utilizadas.

## Fluxo operacional da IA

1. Receber o ficheiro ou documento e registar a sua origem.
2. Extrair os dados por OCR, IDP ou leitura estruturada.
3. Identificar e classificar o tipo de documento.
4. Normalizar datas, valores, moeda, IVA, estado e forma de pagamento.
5. Aplicar sinal negativo obrigatório às notas de crédito.
6. Validar cálculos, campos obrigatórios, duplicações e consistência.
7. Atribuir nível de confiança a cada resultado.
8. Encaminhar exceções e resultados de baixa confiança para revisão humana.
9. Gravar o resultado, as evidências, as alterações e o utilizador responsável no log de auditoria.
10. Atualizar dashboards, alertas e indicadores apenas após a validação aplicável.

## Missão da IA

A Inteligência Artificial do SEO tem como missão transformar dados dispersos em conhecimento acionável, automatizando processos administrativos, financeiros e contabilísticos para aumentar a eficiência operacional, reduzir custos, minimizar erros humanos e fornecer informação estratégica em tempo real.

Mais do que um simples sistema de leitura de documentos, a IA atua como um verdadeiro analista digital da empresa, integrando automação, inteligência documental, análise financeira, apoio contabilístico e business intelligence numa única plataforma.
