import type { DashboardSummary } from "./types";

export const periodData = {
  abril: { label: "Abril 2026", sales: 36600, profit: 6880, margin: 18.8, stalled: 14, expired: 5 },
  maio: { label: "Maio 2026", sales: 41300, profit: 8879, margin: 21.5, stalled: 13, expired: 6 },
  junho: { label: "Junho 2026", sales: 42350, profit: 8920, margin: 21.1, stalled: 18, expired: 7 },
};


export const impactRows = [
  { process: "Relatório mensal", before: "2 horas", after: "10 minutos", impact: "1 h 50 min poupados" },
  { process: "Conferência de movimentos", before: "Manual", after: "Automática", impact: "Erros detetados antes do fecho" },
  { process: "Marketplaces", before: "Disperso", after: "Centralizado", impact: "Margem real visível" },
  { process: "Inventário", before: "Consulta manual", after: "Alertas automáticos", impact: "Produtos parados sinalizados" },
];

export type PeriodKey = keyof typeof periodData;
export type DashboardPeriod = (typeof periodData)[PeriodKey] | (DashboardSummary & { label: string; stalled: number; expired: number });
