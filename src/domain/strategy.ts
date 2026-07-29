export type StrategySignal =
  | "financialImpact"
  | "recurringPain"
  | "proprietaryData"
  | "decisionAutomation"
  | "integration"
  | "saasRevenue"
  | "securityTrust"
  | "simpleProduct"
  | "distribution";

export type StrategyPillar = {
  id: StrategySignal;
  title: string;
  question: string;
  outcome: string;
};

export type StrategyProcessStep = {
  title: string;
  action: string;
  evidence: string;
};

export type SaasPlanStrategy = {
  plan: "Starter" | "Professional" | "Business" | "Enterprise";
  customer: string;
  value: string;
};

export type RoadmapStage = {
  phase: string;
  title: string;
  outcomes: string[];
};

export const strategyNorthStar =
  "O SEO e o copiloto financeiro-operacional das PME: liga dados dispersos, encontra perdas escondidas e transforma operacoes diarias em decisoes de lucro.";

export const strategyPillars: StrategyPillar[] = [
  {
    id: "financialImpact",
    title: "Dor economica recorrente",
    question: "Esta funcionalidade reduz perda, recupera margem ou acelera cobranca todos os meses?",
    outcome: "O cliente ve dinheiro protegido ou recuperado.",
  },
  {
    id: "recurringPain",
    title: "Mercado expansivel",
    question: "A dor existe em muitas PME com inventario, canais de venda, fornecedores ou contabilidade operacional?",
    outcome: "O produto pode sair do nicho inicial e escalar.",
  },
  {
    id: "proprietaryData",
    title: "Dados proprios",
    question: "A funcionalidade cria historico de vendas, inventario, margem, risco, pagamentos ou decisoes?",
    outcome: "O SEO aprende com dados que concorrentes nao possuem.",
  },
  {
    id: "decisionAutomation",
    title: "Automacao de decisao",
    question: "O sistema diz o que comprar, vender, cobrar, negociar ou corrigir?",
    outcome: "O produto deixa de mostrar numeros e passa a orientar acao.",
  },
  {
    id: "integration",
    title: "Integracoes",
    question: "A funcionalidade aproxima o SEO de bancos, faturacao, marketplaces, e-commerce ou folhas de calculo?",
    outcome: "O SEO entra no fluxo real da empresa.",
  },
  {
    id: "saasRevenue",
    title: "Receita SaaS",
    question: "A funcionalidade encaixa num plano Starter, Professional, Business ou Enterprise?",
    outcome: "O valor vira receita recorrente por empresa.",
  },
  {
    id: "securityTrust",
    title: "Seguranca e confianca",
    question: "Respeita autenticacao, permissoes, auditoria, backups, RGPD e isolamento por empresa?",
    outcome: "Empresas confiam dados sensiveis ao produto.",
  },
  {
    id: "simpleProduct",
    title: "Produto simples",
    question: "O cliente entende em segundos o dinheiro em risco e a proxima acao?",
    outcome: "A experiencia fica clara, mesmo com complexidade por baixo.",
  },
  {
    id: "distribution",
    title: "Distribuicao",
    question: "Ajuda contabilistas, consultores, parceiros ou marketplaces a venderem o SEO?",
    outcome: "O produto cresce por canais alem de venda direta.",
  },
];

export const strategyProcessSteps: StrategyProcessStep[] = [
  {
    title: "Definir a dor economica",
    action: "Escrever que perda mensal a funcionalidade combate.",
    evidence: "Exemplo: stock parado, margem baixa, cobranca atrasada ou erro de conciliacao.",
  },
  {
    title: "Definir a decisao recomendada",
    action: "Converter o insight numa acao objetiva para o cliente.",
    evidence: "Exemplo: cobrar este cliente, baixar este preco, nao recomprar este SKU.",
  },
  {
    title: "Guardar historico",
    action: "Persistir dado, decisao, utilizador, data, resultado e impacto estimado.",
    evidence: "O historico alimenta comparacoes e IA proprietaria.",
  },
  {
    title: "Medir antes e depois",
    action: "Comparar diario, semanal, mensal, trimestral e anual quando fizer sentido.",
    evidence: "Usar capital em risco, margem, stock parado, saldos e pendencias.",
  },
  {
    title: "Aplicar seguranca desde o inicio",
    action: "Garantir permissao, auditoria, segregacao por empresa e preparacao para backup.",
    evidence: "Confianca e funcionalidade de produto.",
  },
  {
    title: "Encaixar no SaaS",
    action: "Definir que plano captura o valor da funcionalidade.",
    evidence: "Starter, Professional, Business ou Enterprise.",
  },
];

export const saasPlanStrategy: SaasPlanStrategy[] = [
  {
    plan: "Starter",
    customer: "PME pequena",
    value: "Importacao, dashboard, relatorio e historico basico.",
  },
  {
    plan: "Professional",
    customer: "Empresa com inventario e financeiro",
    value: "IA, snapshots, cobranca, conciliacao e decisoes priorizadas.",
  },
  {
    plan: "Business",
    customer: "Operacao multiempresa ou mais complexa",
    value: "Integracoes, auditoria, permissoes e automacoes.",
  },
  {
    plan: "Enterprise",
    customer: "Parceiros, grupos e consultoras",
    value: "API, compliance, suporte, SLA e customizacoes.",
  },
];

export const roadmapStages: RoadmapStage[] = [
  {
    phase: "Fase 1",
    title: "Produto que prova valor",
    outcomes: ["dados reais", "dinheiro em risco", "decisoes priorizadas", "snapshots", "relatorio executivo"],
  },
  {
    phase: "Fase 2",
    title: "SaaS confiavel",
    outcomes: ["PostgreSQL cloud", "backups", "MFA real", "billing Stripe", "permissoes", "observabilidade"],
  },
  {
    phase: "Fase 3",
    title: "Integracoes",
    outcomes: ["bancos", "faturacao", "marketplaces", "e-commerce", "contabilidade", "APIs"],
  },
  {
    phase: "Fase 4",
    title: "IA defensavel",
    outcomes: ["historico por setor", "preco sugerido", "previsao de stock", "previsao de cobranca", "margem real"],
  },
  {
    phase: "Fase 5",
    title: "Escala",
    outcomes: ["parceiros", "onboarding self-service", "templates por setor", "marketplace de integracoes", "Enterprise API"],
  },
];

export function scoreStrategyFit(signals: StrategySignal[]) {
  const uniqueSignals = new Set(signals);
  const score = Math.round((uniqueSignals.size / strategyPillars.length) * 100);
  const missing = strategyPillars.filter((pillar) => !uniqueSignals.has(pillar.id)).map((pillar) => pillar.title);
  const decision = score >= 70 ? "Construir agora" : score >= 45 ? "Refinar antes de construir" : "Nao priorizar";
  return { score, decision, missing };
}
