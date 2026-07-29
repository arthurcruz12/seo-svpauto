import { describe, expect, it } from "vitest";
import { calculateOperationalScore } from "./operationalScore";

describe("calculateOperationalScore", () => {
  it("returns 100 only when every measured dimension is controlled", () => {
    expect(calculateOperationalScore({
      totalIssues: 10,
      unresolvedIssues: 0,
      totalDebts: 10,
      overdueDebts: 0,
      totalInventory: 20,
      inventoryDivergences: 0,
      criticalStock: 0,
      stalledProducts: 0,
    }).score).toBe(100);
  });

  it("applies proportional weights instead of an artificial minimum", () => {
    expect(calculateOperationalScore({
      totalIssues: 10,
      unresolvedIssues: 10,
      totalDebts: 10,
      overdueDebts: 10,
      totalInventory: 10,
      inventoryDivergences: 10,
      criticalStock: 10,
      stalledProducts: 10,
    }).score).toBe(0);
  });

  it("does not penalize dimensions without imported observations", () => {
    expect(calculateOperationalScore({
      totalIssues: 0,
      unresolvedIssues: 0,
      totalDebts: 0,
      overdueDebts: 0,
      totalInventory: 0,
      inventoryDivergences: 0,
      criticalStock: 0,
    }).score).toBe(100);
  });
});
