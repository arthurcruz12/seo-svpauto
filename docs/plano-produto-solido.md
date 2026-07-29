# SEO - Plano para Produto Sólido

Este documento separa o que já funciona no MVP do que deve ser evoluído para transformar o SEO num produto empresarial real.

## Estado atual

- Interface web em React, TypeScript e TailwindCSS.
- Fluxo com página de produto, login, segunda autenticação demonstrativa e upload de ficheiro.
- Leitura de ficheiros Excel, CSV e TXT no browser.
- Classificação automática de movimentos por regras SNC.
- Dashboard, inventário, financeiro, conciliação e IA Analista em versão MVP.
- Validação básica de formato e tamanho dos ficheiros importados.

## Limites assumidos

- A autenticação atual é demonstrativa e não substitui backend real.
- A segunda autenticação usa código fixo apenas para apresentação.
- Os dados importados são processados no browser, sem base de dados persistente.
- As contas SNC sugeridas são apoio de análise e devem ser validadas por contabilista certificado.

## Próximas etapas técnicas

1. Criar backend com FastAPI.
2. Guardar dados em PostgreSQL.
3. Implementar autenticação real com utilizadores, perfis e sessões.
4. Adicionar MFA real por email, app autenticadora ou SMS.
5. Criar logs de auditoria para importações, alterações e exportações.
6. Mover parsing de Excel para backend isolado.
7. Substituir ou isolar a dependência `xlsx`, que possui advisories de segurança.
8. Adicionar permissões por módulo: administração, financeiro, inventário e leitura.
9. Criar testes automatizados para importação, classificação e cálculos.
10. Separar o frontend em componentes e serviços menores.

## Critério de produto

O SEO deixa de ser apenas um protótipo quando:

- cada ficheiro importado fica registado;
- cada alteração tem utilizador, data e histórico;
- os dados são persistidos numa base de dados;
- utilizadores têm permissões diferentes;
- relatórios podem ser reproduzidos;
- regras contabilísticas são versionadas;
- backups e exportações seguem rotina definida.

## Processo de decisão

A evolução do produto passa a seguir a estratégia de escala descrita em [estrategia-bilionaria.md](estrategia-bilionaria.md) e o processo prático descrito em [processo-execucao-estrategia.md](processo-execucao-estrategia.md).

Cada nova funcionalidade deve provar pelo menos um destes impactos:

- reduzir perdas mensais;
- recuperar margem;
- acelerar cobrança;
- diminuir stock parado;
- reduzir erros de conciliação, fiscais ou contabilísticos;
- criar histórico operacional proprietário;
- aumentar segurança e confiança empresarial;
- fortalecer receita recorrente SaaS;
- facilitar distribuição por parceiros.

O critério deixa de ser "adicionar mais uma tela" e passa a ser "gerar uma decisão de lucro mais clara para o cliente".

## Posicionamento

O SEO deve ser apresentado como uma plataforma de eficiência operacional para empresas com dados dispersos em Excel, marketplaces, inventário e documentos financeiros.

O objetivo não é substituir processos imediatamente, mas provar valor com dados reais e depois evoluir gradualmente para um ERP operacional.
