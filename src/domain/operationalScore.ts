export type OperationalScoreInput = {
  totalIssues: number;
  unresolvedIssues: number;
  totalDebts: number;
  overdueDebts: number;
  totalInventory: number;
  inventoryDivergences: number;
  criticalStock: number;
  stalledProducts?: number;
};

function failureRate(failures: number, total: number) {
  if (total <= 0) return 0;
  return Math.min(1, Math.max(0, failures / total));
}

/**
 * Objective 0-100 score. Each dimension has an explicit maximum weight;
 * adding more records cannot artificially improve the result.
 */
export function calculateOperationalScore(input: OperationalScoreInput) {
  const penalties = {
    anomalies: failureRate(input.unresolvedIssues, input.totalIssues) * 35,
    overduePayments: failureRate(input.overdueDebts, input.totalDebts) * 25,
    inventoryDivergences: failureRate(input.inventoryDivergences, input.totalInventory) * 20,
    criticalStock: failureRate(input.criticalStock, input.totalInventory) * 10,
    stalledStock: failureRate(input.stalledProducts ?? 0, input.totalInventory) * 10,
  };
  const totalPenalty = Object.values(penalties).reduce((sum, value) => sum + value, 0);
  return {
    score: Math.max(0, Math.min(100, Math.round(100 - totalPenalty))),
    penalties,
  };
}
