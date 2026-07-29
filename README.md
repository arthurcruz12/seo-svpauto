# SEO - Sistema de Eficiência Operacional

O **SEO - Sistema de Eficiência Operacional** é uma ferramenta de apoio à análise, organização e decisão para uma empresa de comércio de peças automóveis.

O projeto nasce no contexto de um estágio curricular em Economia e tem como objetivo resolver problemas reais ligados a processos operacionais atualmente suportados por Excel, documentos manuais, mapas separados e rotinas pouco automatizadas.

## Filosofia do projeto

O SEO não deve ser apresentado como uma substituição imediata dos processos atuais da empresa.

A abordagem correta é introduzir o sistema como uma ferramenta paralela de apoio à análise e à decisão. Numa primeira fase, o SEO deve coexistir com os processos existentes, permitindo comparar resultados, validar dados e demonstrar ganhos concretos sem criar resistência operacional.

A estratégia do projeto é:

1. Mostrar funcionalidade real.
2. Reduzir tempo em tarefas repetitivas.
3. Diminuir erros de registo e consolidação.
4. Melhorar a organização da informação.
5. Apoiar decisões com indicadores claros.
6. Propor melhorias apenas depois de demonstrar valor prático.

Esta filosofia permite que a empresa ganhe confiança no sistema gradualmente. Primeiro observa-se o benefício; depois avalia-se a evolução dos processos.

## Problema operacional

A empresa trabalha com loja física, loja online, marketplaces, clientes, fornecedores, documentos contabilísticos, mapas de caixa, mapas de quilómetros, inventário e análise mensal de resultados.

Atualmente, grande parte desta informação encontra-se dispersa, exigindo trabalho manual para consolidar dados e interpretar resultados.

O SEO pretende centralizar essa informação de forma progressiva, mantendo o foco em utilidade prática, simplicidade de utilização e melhoria da qualidade dos dados.

## Objetivos principais

- Centralizar dados operacionais, financeiros e comerciais.
- Apoiar a gestão diária da empresa.
- Reduzir a dependência de ficheiros Excel isolados.
- Facilitar a análise mensal de resultados.
- Melhorar o controlo de inventário.
- Comparar desempenho por canal de venda.
- Apoiar decisões com indicadores objetivos.
- Criar uma base técnica que possa evoluir depois do estágio.

## Objetivo central

Criar um sistema inteligente, simples e visualmente profissional que centralize dados operacionais, financeiros e comerciais, permitindo à empresa analisar desempenho, controlar inventário, acompanhar clientes e fornecedores, reconciliar movimentos e gerar relatórios automáticos.

## Comparação Antes/Depois

O SEO deve mostrar claramente o impacto da sua utilização através de uma comparação entre o processo atual e o processo apoiado pelo sistema.

Antes:

- Processo manual.
- Vários ficheiros.
- Maior risco de erro.
- Mais tempo gasto.

Depois:

- Dados centralizados.
- Relatórios automáticos.
- Menos erros.
- Mais rapidez.
- Melhor decisão.

Cada módulo deve incluir pelo menos uma métrica de impacto, como tempo poupado, erros identificados, processos automatizados ou melhoria na visibilidade dos dados.

## Módulos previstos

- Dashboard executivo.
- Conciliação operacional.
- Análise financeira.
- Análise de marketplaces.
- Contas correntes.
- Inventário inteligente.
- Business Intelligence.
- IA Analista.

Os requisitos detalhados dos módulos estão descritos em [docs/requisitos-funcionais.md](docs/requisitos-funcionais.md).

As decisões iniciais de interface, conjunto tecnológico e arquitetura estão descritas em [docs/arquitetura-e-design.md](docs/arquitetura-e-design.md).

A proposta completa para apresentação à administração e enquadramento académico está em [docs/proposta-projeto.md](docs/proposta-projeto.md).

A visão de escala para transformar o SEO num SaaS de grande valor está em [docs/estrategia-bilionaria.md](docs/estrategia-bilionaria.md).

O processo prático para aplicar essa estratégia em cada decisão de produto e tecnologia está em [docs/processo-execucao-estrategia.md](docs/processo-execucao-estrategia.md).

## Primeira versão viável

A primeira versão deve ser pequena, demonstrável e focada em valor real.

Funcionalidades prioritárias:

- Registo de vendas.
- Registo de despesas.
- Registo de inventário.
- Mapa de caixa.
- Dashboard mensal.
- Relatório simples de resultados.
- Importação ou exportação em formato Excel/CSV.

## Protótipo web

O projeto inclui um protótipo frontend do SEO desenvolvido com React, TypeScript, TailwindCSS e Recharts.

Funcionalidades já interativas:

- Ecrã inicial que pede a planilha Excel antes de entrar no sistema.
- Leitura de ficheiros `.xlsx`, `.xls`, `.csv` e `.txt` no browser.
- Processamento automático da planilha pela IA para alimentar SNC, inventário, financeiro e dashboard.
- Inteligência documental para Excel, CSV, TXT e XML/SAF-T, com classificação de faturas, faturas-recibo, recibos, notas de crédito e notas de débito.
- Validação automática de valor líquido + IVA = total, datas, possíveis duplicados e normalização negativa de notas de crédito.
- Estado financeiro por documento (pago, pendente, vencido ou desconhecido), confiança, revisão humana e trilho de auditoria.
- Resumo documental com totais líquidos, IVA, total, documentos válidos, alertas e vencimentos.
- Navegação entre Dashboard, Conciliação, Financeiro, Inventário e IA Analista.
- Filtro de período no Dashboard.
- Exportação de relatório CSV.
- Exportação de métricas Antes/Depois.
- Importação simples de ficheiros CSV/TXT para conciliação.
- Resolução de problemas de conciliação.
- Filtros e marcação de contas correntes como pagas.
- Pesquisa no inventário.
- Registo de saída de stock.
- IA Analista com respostas por tema, confiança, nível de risco, prioridades e plano de ação.
- Centro de Inteligência Operacional no Dashboard com resumo executivo da IA, criticidade, impacto financeiro, impacto operacional, tempo estimado, pontuação SEO e ação recomendada.
- Classificação SNC de ficheiros CSV/TXT com sugestão automática de contas do código de contas português.

Formato recomendado para classificação SNC:

```csv
data;descricao;entidade;valor
2026-06-02;Venda loja online peça BMW;Cliente Online;450,00
2026-06-03;Comissão Ovoko marketplace;Ovoko;-38,50
```

As contas SNC sugeridas são uma ajuda à análise e devem ser validadas por contabilista certificado antes de qualquer lançamento oficial.

Para executar localmente:

```powershell
npm.cmd install
npm.cmd run dev
```

Para validar a compilação:

```powershell
npm.cmd run build
```

## OCR local multipágina

Na área **Documentos**, o utilizador pode selecionar um único PDF ou imagem. O sistema lê todas as páginas, utiliza o texto incorporado quando disponível e aplica Tesseract OCR apenas nas páginas digitalizadas. São suportados PDF, PNG, JPG/JPEG, TIFF multipágina e WEBP, com limite de 25 MB.

Variáveis opcionais:

```text
OCR_LANGUAGE=por+eng
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

No Windows, instale o Tesseract com os idiomas português e inglês e configure `TESSERACT_CMD` quando o executável não estiver no `PATH`. Em Docker, os idiomas são instalados automaticamente:

```powershell
docker compose up --build
```

O backend local continua disponível com `scripts\start-local.cmd`. A documentação e o teste manual do endpoint estão em [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs), rota `POST /api/v1/documents/ocr`. O endpoint exige JWT, permissão `documents:write` e o `company_id` do utilizador autenticado.

## Critérios de sucesso

O projeto será considerado bem-sucedido se conseguir demonstrar:

- Menos tempo gasto na preparação de mapas e relatórios.
- Menos duplicação de dados.
- Maior facilidade em perceber o resultado mensal.
- Melhor visibilidade sobre vendas por canal.
- Melhor organização do inventário.
- Maior capacidade de tomar decisões com base em dados.

## Princípio orientador

O SEO deve ser útil antes de ser completo.

A prioridade não é substituir todos os processos desde o primeiro dia, mas provar que uma ferramenta simples, bem desenhada e ligada à realidade da empresa pode melhorar a eficiência operacional.
