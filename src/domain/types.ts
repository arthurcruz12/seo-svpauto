export type SectionId = "dashboard" | "documentos" | "conciliacao" | "financeiro" | "inventario" | "ia" | "nuvem" | "estrategia";
export type AppScreen = "landing" | "login" | "register" | "mfa" | "onboarding" | "app";
export type MetricTone = "navy" | "success" | "warning" | "danger";
export type IssueStatus = "Rever" | "Alerta" | "Classificar" | "Resolvido";
export type DebtState = "Em atraso" | "A vencer" | "Pago";

export type ReconciliationIssue = {
  id: number;
  document: string;
  source: string;
  value: string;
  issue: string;
  status: IssueStatus;
};

export type InventoryItem = {
  ref: string;
  product: string;
  stock: number;
  lastSaleDays: number;
  margin: number;
  alert: string;
  unit: string;
  stockType: string;
  movementType: "Compra" | "Venda" | "Sucata" | "Existente";
  movementQuantity: number;
  warehouse: string;
  systemQuantity: number;
  physicalQuantity: number;
  differenceQuantity: number;
  unitCost: number;
  stockValue: number;
  location: string;
  validationState: string;
  confidence: number;
};

export type DebtItem = {
  id: number;
  invoice: string;
  entity: string;
  type: "Cliente" | "Fornecedor";
  amount: number;
  issueDate: string;
  dueDate: string;
  dueDays: number;
  state: DebtState;
};

export type AiAnalysis = {
  answer: string;
  confidence: number;
  risk: "Baixo" | "Médio" | "Elevado";
  priorities: string[];
  actions: string[];
  intent?: string;
  nextQuestions?: string[];
  conversationId?: string;
  provider?: "openai" | "analytical-fallback";
  explainability?: {
    dataSources: string[];
    financialImpact: number;
    signals: string[];
    method: string;
    humanReview: string;
  };
};

export type DecisionPriority = {
  title: string;
  criticality: "Crítica" | "Atenção" | "Monitorização";
  financialImpact: string;
  operationalImpact: string;
  resolutionTime: string;
  recommendation: string;
  score: number;
  unresolvedPenalty: number;
  action: string;
  tone: MetricTone;
  target: SectionId;
};

export type DashboardSummary = {
  sourceName: string;
  rowsRead: number;
  sales: number;
  expenses: number;
  profit: number;
  margin: number;
};

export type ImportedDataset = {
  summary: DashboardSummary;
  classifiedMovements: ClassifiedMovement[];
  inventory: InventoryItem[];
  debts: DebtItem[];
  issues: ReconciliationIssue[];
  documentIntelligence: DocumentIntelligence;
  storedFile?: CloudFile;
  generatedFile?: CloudFile;
  billingTransform?: {
    sourceRows: number;
    includedRows: number;
    excludedCancelled: number;
    excludedNonBilling: number;
    groups: Record<string, number>;
    totalRow: number;
    totalAmount: number;
  };
  rowErrors?: Array<{ row: number; document: string; errors: string[] }>;
};

export type DocumentRecord = {
  id: string;
  number: string;
  date: string;
  entity: string;
  documentType: string;
  financialState: "Pago" | "Pendente" | "Vencido" | "Desconhecido";
  netAmount: number;
  vatAmount: number;
  totalAmount: number;
  confidence: number;
  validations: string[];
  needsReview: boolean;
};

export type DocumentIntelligence = {
  sourceFormat: string;
  documents: DocumentRecord[];
  totals: { net: number; vat: number; total: number };
  stats: { processed: number; valid: number; review: number; duplicates: number; overdue: number; corrected: number };
  auditTrail: string[];
};

export type OcrResult = {
  message: string;
  filename: string;
  content_type: string;
  page_count: number;
  pages: Array<{ page: number; method: "embedded_text" | "ocr"; text: string }>;
  full_text: string;
};

export type SnapshotPeriod = "daily" | "weekly" | "monthly" | "quarterly" | "annual";

export type MetricSnapshot = {
  id: string;
  companyId: string;
  period: SnapshotPeriod;
  label: string;
  metrics: Record<string, number | string>;
  createdAt: string;
  reportDate: string;
};

export type SnapshotComparison = {
  period: SnapshotPeriod;
  current: Record<string, number | string>;
  previous: Record<string, number | string> | null;
  delta: Record<string, number>;
  message?: string;
};

export type BillingSubscription = {
  companyId: string;
  plan: string;
  status: string;
  currentPeriodEnd?: string;
};

export type CloudFile = {
  id: string;
  filename: string;
  contentType: string;
  category: string;
  sizeBytes: number;
  sha256: string;
  uploadedAt: string;
};

export type ClassifiedMovement = {
  id: number;
  date: string;
  description: string;
  entity: string;
  amount: number;
  accountCode: string;
  accountName: string;
  movementType: "Débito" | "Crédito";
  confidence: number;
  reason: string;
};

export type AccountRule = {
  code: string;
  name: string;
  keywords: string[];
  defaultType: "Débito" | "Crédito";
  reason: string;
};
