import type {
  BillingSubscription,
  CloudFile,
  DashboardSummary,
  DebtItem,
  DocumentIntelligence,
  InventoryItem,
  MetricSnapshot,
  ReconciliationIssue,
  SnapshotComparison,
  SnapshotPeriod,
} from "../domain/types";
import { apiRequest } from "./api";

export async function resolveIssueApi(accessToken: string, id: number): Promise<ReconciliationIssue> {
  return request(`/reconciliation/issues/${id}/resolve`, accessToken, { method: "POST" });
}

export async function listIssuesApi(accessToken: string): Promise<ReconciliationIssue[]> {
  return request("/reconciliation/issues", accessToken, { method: "GET" });
}

export async function getDashboardStateApi(accessToken: string): Promise<{
  sourceName: string;
  summary: DashboardSummary | null;
  documentIntelligence: DocumentIntelligence | null;
  updatedAt: string | null;
}> {
  return request("/dashboard/state", accessToken, { method: "GET" });
}

export async function resolveAllIssuesApi(accessToken: string): Promise<ReconciliationIssue[]> {
  return request("/reconciliation/issues/resolve-all", accessToken, { method: "POST" });
}

export async function listInventoryItemsApi(accessToken: string): Promise<InventoryItem[]> {
  return request("/inventory/items", accessToken, { method: "GET" });
}

export async function registerInventorySaleApi(accessToken: string, ref: string): Promise<InventoryItem> {
  return request(`/inventory/items/${encodeURIComponent(ref)}/sale`, accessToken, { method: "POST" });
}

export async function listDebtItemsApi(accessToken: string): Promise<DebtItem[]> {
  return request("/finance/debts", accessToken, { method: "GET" });
}

export async function markDebtPaidApi(accessToken: string, id: number): Promise<DebtItem> {
  return request(`/finance/debts/${id}/pay`, accessToken, { method: "POST" });
}

export async function importReconciliationApi(accessToken: string, file: File): Promise<ReconciliationIssue[]> {
  const form = new FormData();
  form.append("file", file);
  return request("/reconciliation/import", accessToken, { method: "POST", body: form });
}

export async function createMetricSnapshotApi(
  accessToken: string,
  period: SnapshotPeriod,
  label?: string,
  reportDate?: string,
): Promise<MetricSnapshot> {
  return request("/reports/snapshots", accessToken, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ period, label, report_date: reportDate }),
  });
}

export async function listMetricSnapshotsApi(accessToken: string, period: SnapshotPeriod, reportDate?: string): Promise<MetricSnapshot[]> {
  const dateQuery = reportDate ? `&report_date=${encodeURIComponent(reportDate)}` : "";
  return request(`/reports/snapshots?period=${encodeURIComponent(period)}&limit=120${dateQuery}`, accessToken, { method: "GET" });
}

export async function compareMetricSnapshotsApi(accessToken: string, period: SnapshotPeriod): Promise<SnapshotComparison> {
  return request(`/reports/compare?period=${encodeURIComponent(period)}`, accessToken, { method: "GET" });
}

export async function getBillingSubscriptionApi(accessToken: string): Promise<BillingSubscription> {
  return request("/billing/subscription", accessToken, { method: "GET" });
}

export async function createBillingCheckoutApi(accessToken: string, plan: string): Promise<{ checkoutUrl: string }> {
  return request("/billing/checkout", accessToken, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan }),
  });
}

export async function listCloudFilesApi(accessToken: string): Promise<CloudFile[]> {
  return request("/cloud/files?limit=100", accessToken, { method: "GET" });
}

async function request<T>(path: string, accessToken: string, init: RequestInit): Promise<T> {
  return apiRequest<T>(path, accessToken, init);
}
