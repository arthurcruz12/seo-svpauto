# Conformidade legal, contabilistica e operacional do SEO

Este documento define o enquadramento de conformidade do SEO enquanto ferramenta de apoio a decisao. O sistema nao substitui contabilista certificado, jurista, encarregado de protecao de dados ou auditor.

## SNC Portugal

Referencia principal: Decreto-Lei n.º 158/2009, de 13 de julho, que aprova o Sistema de Normalizacao Contabilistica.

O SEO usa classes de contas do SNC para sugerir classificacoes operacionais:

- 11 Caixa
- 12 Depositos a ordem
- 21 Clientes
- 22 Fornecedores
- 24 Estado e outros entes publicos
- 31 Compras
- 32 Mercadorias
- 61 Custo das mercadorias vendidas e das materias consumidas
- 62 Fornecimentos e servicos externos
- 63 Gastos com o pessoal
- 68 Outros gastos e perdas
- 71 Vendas
- 72 Prestacoes de servicos
- 78 Outros rendimentos e ganhos

Regra obrigatoria do produto: qualquer classificacao gerada pela IA e uma sugestao. Lancamentos oficiais, demonstracoes financeiras e declaracoes fiscais devem ser validados por contabilista certificado.

## RGPD

O SEO deve aplicar os principios de finalidade, licitude, transparencia, minimizacao, exatidao, limitacao da conservacao, integridade, confidencialidade e responsabilidade demonstravel.

Medidas implementadas nesta versao:

- palavras-passe removidas do frontend;
- autenticacao e segunda verificacao no backend;
- tokens de sessao com expiracao;
- permissoes por perfil;
- upload Excel processado no backend;
- auditoria de acoes sensiveis;
- pseudonimizacao do ator nos logs;
- tamanho maximo de ficheiro;
- dados ficticios fora da plataforma autenticada.

Medidas obrigatorias antes de producao real:

- definir responsavel pelo tratamento e subcontratantes;
- aprovar politica de privacidade e termos;
- configurar segredo JWT forte por variavel de ambiente;
- ativar HTTPS;
- encriptar dados em repouso;
- definir prazos de retencao e apagamento;
- implementar backups e plano de resposta a incidentes;
- realizar revisao juridica e contabilistica.

## AI Act

O SEO deve identificar quando ha recomendacao automatizada e manter supervisao humana. A IA nao deve tomar decisoes oficiais autonomas sobre contabilidade, fiscalidade, credito, emprego ou direitos de pessoas.

Medidas de produto:

- classificacao SNC com nivel de confianca;
- explicacao do motivo da classificacao;
- aprovacao humana obrigatoria;
- logs de classificacoes e exportacoes;
- possibilidade de corrigir classificacoes antes de qualquer uso oficial.

## Tratados e valores da Uniao Europeia

O produto deve respeitar Estado de direito, direitos fundamentais, igualdade, nao discriminacao e protecao de dados pessoais. A finalidade do SEO e apoiar decisao empresarial, nao substituir deveres legais, fiscais ou contabilisticos.

## Estado atual

Base tecnica mais solida para ambiente piloto controlado:

- frontend sem armazenamento de credenciais;
- backend com autenticacao, MFA, permissoes e auditoria;
- leitura Excel removida do navegador;
- sugestao SNC auditavel;
- documentacao de privacidade e checklist de producao.

Ainda nao deve ser vendido como juridicamente certificado sem revisao profissional, contratos, infraestrutura segura e politicas aprovadas pela empresa.
