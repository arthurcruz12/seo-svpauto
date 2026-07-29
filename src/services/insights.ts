import type { AiAnalysis, DecisionPriority } from "../domain/types";

export function buildDecisionPriorities(
  unresolvedIssues: number,
  stalledProducts: number,
  activeDebts: number,
): DecisionPriority[] {
  const issueImpact = unresolvedIssues * 320;
  const inventoryImpact = stalledProducts * 75;
  const debtImpact = activeDebts * 190;

  const priorities: DecisionPriority[] = [
    {
      title: "Fecho mensal com pendências",
      criticality: unresolvedIssues > 0 ? "Crítica" : "Monitorização",
      financialImpact: `Protege cerca de ${issueImpact.toLocaleString("pt-PT")} EUR em validação`,
      operationalImpact: "Reduz risco de erro contabilístico e retrabalho no fecho mensal",
      resolutionTime: unresolvedIssues > 0 ? "12 minutos" : "Sem ação imediata",
      recommendation:
        unresolvedIssues > 0
          ? `Validar ${unresolvedIssues} movimentos pendentes antes de exportar o relatório.`
          : "Manter validação final antes da exportação executiva.",
      score: unresolvedIssues > 0 ? 4 : 1,
      unresolvedPenalty: unresolvedIssues > 0 ? -3 : 0,
      action: unresolvedIssues > 0 ? "Resolver Agora" : "Monitorizar",
      tone: unresolvedIssues > 0 ? "danger" : "success",
      target: "conciliacao",
    },
    {
      title: "Capital parado no inventário",
      criticality: stalledProducts > 0 ? "Atenção" : "Monitorização",
      financialImpact: `Pode libertar ${inventoryImpact.toLocaleString("pt-PT")} EUR em stock parado`,
      operationalImpact: "Melhora liquidez, espaço útil e prioridade de reposição",
      resolutionTime: stalledProducts > 0 ? "18 minutos" : "Sem ação imediata",
      recommendation:
        stalledProducts > 0
          ? `Rever preço, exposição e rotação de ${stalledProducts} produtos parados há mais de 90 dias.`
          : "Continuar a acompanhar produtos sem rotação.",
      score: stalledProducts > 0 ? 3 : 1,
      unresolvedPenalty: stalledProducts > 0 ? -2 : 0,
      action: stalledProducts > 0 ? "Resolver Agora" : "Monitorizar",
      tone: stalledProducts > 0 ? "warning" : "success",
      target: "inventario",
    },
    {
      title: "Saldos por regularizar",
      criticality: activeDebts > 0 ? "Atenção" : "Monitorização",
      financialImpact: `Acompanha ${debtImpact.toLocaleString("pt-PT")} EUR em risco operacional`,
      operationalImpact: "Reduz atrasos em recebimentos, pagamentos e conciliação bancária",
      resolutionTime: activeDebts > 0 ? "9 minutos" : "Sem ação imediata",
      recommendation:
        activeDebts > 0
          ? `Ordenar ${activeDebts} contas abertas por antiguidade e tratar primeiro saldos vencidos.`
          : "Manter contas correntes sem saldos críticos.",
      score: activeDebts > 0 ? 2 : 1,
      unresolvedPenalty: activeDebts > 0 ? -1 : 0,
      action: activeDebts > 0 ? "Resolver Agora" : "Monitorizar",
      tone: activeDebts > 0 ? "navy" : "success",
      target: "financeiro",
    },
  ];

  return priorities.sort((a, b) => b.score - a.score);
}

export function buildAiAnalysis(question: string): AiAnalysis {
  const normalized = question.toLowerCase();
  const baseExplainability = {
    dataSources: ["dados locais", "inventário", "contas correntes", "conciliação"],
    financialImpact: 0,
    signals: ["Sem backend ativo", "Resposta local de fallback", "Carregue um ficheiro para análise real"],
    method: "Fallback local baseado em regras de intenção. A análise completa usa o backend e dados persistidos.",
    humanReview: "Obrigatória para SNC, fiscalidade e decisões oficiais.",
  };

  if (normalized.includes("lucro") || normalized.includes("margem")) {
    return {
      answer:
        "Depois da importação, a IA cruza receitas, despesas, margem e pendências para indicar onde o resultado mensal está a ser afetado.",
      confidence: 78,
      risk: "Médio",
      priorities: ["Validar movimentos pendentes", "Confirmar custos por plataforma", "Comparar margem mensal"],
      actions: ["Fechar conciliação", "Exportar relatório mensal", "Rever despesas com maior peso"],
      intent: "financeiro",
      nextQuestions: ["Onde estou a perder margem?", "Que despesas mais afetam o resultado?"],
      explainability: baseExplainability,
    };
  }

  if (normalized.includes("cliente") || normalized.includes("atraso") || normalized.includes("dívida")) {
    return {
      answer:
        "A prioridade deve ser ordenar saldos por antiguidade e tratar primeiro clientes com maior impacto financeiro.",
      confidence: 76,
      risk: "Elevado",
      priorities: ["Clientes com maior antiguidade", "Saldos acima de 500 EUR", "Documentos sem contacto recente"],
      actions: ["Gerar lista de cobrança", "Marcar contas pagas após confirmação", "Criar alerta para próximos vencimentos"],
      intent: "cobranca",
      nextQuestions: ["Quais saldos devo cobrar primeiro?", "Qual valor está em atraso?"],
      explainability: baseExplainability,
    };
  }

  if (normalized.includes("parado") || normalized.includes("stock") || normalized.includes("inventário")) {
    return {
      answer:
        "A IA procura produtos parados, stock crítico e baixa margem para separar ações de liquidação, reposição e revisão de preço.",
      confidence: 80,
      risk: "Médio",
      priorities: ["Produtos sem venda há mais de 90 dias", "Referências com stock igual ou inferior a 1", "Peças com margem inferior a 15%"],
      actions: ["Registar saídas de stock", "Rever preço dos produtos parados", "Priorizar reposição das referências críticas"],
      intent: "inventario",
      nextQuestions: ["Quais produtos devo liquidar primeiro?", "Onde há risco de ruptura?"],
      explainability: baseExplainability,
    };
  }

  return {
    answer:
      "A IA recomenda começar pelo Centro de Decisão: resolver pendências, rever capital parado e validar contas abertas antes do relatório executivo.",
    confidence: 74,
    risk: "Médio",
    priorities: ["Qualidade dos dados", "Visibilidade financeira", "Eficiência operacional"],
    actions: ["Importar dados reais", "Resolver alertas", "Exportar relatório executivo"],
    intent: "executivo",
    nextQuestions: ["O que devo resolver primeiro?", "Qual é o maior impacto financeiro?"],
    explainability: baseExplainability,
  };
}
