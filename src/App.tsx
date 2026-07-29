import { useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useEffect } from "react";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  BarChart3,
  BookOpenCheck,
  Bot,
  Boxes,
  Building2,
  Cloud,
  Clock3,
  CheckCircle2,
  ClipboardCheck,
  CalendarDays,
  CreditCard,
  Download,
  Files,
  Euro,
  FileSpreadsheet,
  LayoutDashboard,
  PackageSearch,
  Plus,
  Mic,
  AudioLines,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  Upload,
  WalletCards,
  type LucideIcon,
} from "lucide-react";
import type {
  AiAnalysis,
  AppScreen,
  ClassifiedMovement,
  DashboardSummary,
  DebtItem,
  DebtState,
  DecisionPriority,
  DocumentIntelligence,
  BillingSubscription,
  CloudFile,
  InventoryItem,
  ImportedDataset,
  MetricSnapshot,
  MetricTone,
  OcrResult,
  ReconciliationIssue,
  SectionId,
  SnapshotComparison,
  SnapshotPeriod,
} from "./domain/types";
import { accountRules } from "./domain/accounts";
import { impactRows, periodData, type PeriodKey } from "./domain/config";
import {
  roadmapStages,
  saasPlanStrategy,
  scoreStrategyFit,
  strategyNorthStar,
  strategyPillars,
  strategyProcessSteps,
  type StrategySignal,
} from "./domain/strategy";
import { downloadCsv, formatCurrency } from "./lib/format";
import { auditAction, configurePersistentAudit } from "./services/audit";
import { calculateOperationalScore } from "./domain/operationalScore";
import { API_BASE_URL } from "./services/api";
import { askBackendAi } from "./services/ai";
import { readDocumentOcr } from "./services/ocr";
import {
  authenticateAccount,
  hasPermission,
  registerClientAccount,
  verifySecurityCode,
  type LocalAccount,
  type SecurityChallenge,
} from "./services/auth";
import { buildAiAnalysis, buildDecisionPriorities } from "./services/insights";
import {
  compareMetricSnapshotsApi,
  createBillingCheckoutApi,
  createMetricSnapshotApi,
  getDashboardStateApi,
  getBillingSubscriptionApi,
  listCloudFilesApi,
  listDebtItemsApi,
  listInventoryItemsApi,
  listIssuesApi,
  importReconciliationApi,
  listMetricSnapshotsApi,
  markDebtPaidApi,
  registerInventorySaleApi,
  resolveAllIssuesApi,
  resolveIssueApi,
} from "./services/operations";
import {
  buildMonthlyChartData,
  buildOperationalDatasetFromFile,
  buildPlatformChartData,
  OPERATIONAL_FILE_EXTENSIONS,
  TEXT_FILE_EXTENSIONS,
  validateUploadFile,
} from "./services/importer";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const navItems: Array<{ id: SectionId; label: string; icon: LucideIcon }> = [
  { id: "dashboard", label: "Início", icon: LayoutDashboard },
  { id: "ia", label: "Assistente IA", icon: Bot },
  { id: "documentos", label: "Documentos", icon: Files },
  { id: "financeiro", label: "Pagamentos", icon: WalletCards },
  { id: "inventario", label: "Inventário", icon: Boxes },
  { id: "conciliacao", label: "Anomalias", icon: AlertTriangle },
  { id: "nuvem", label: "Ficheiros", icon: Upload },
  { id: "nuvem", label: "Auditoria", icon: ClipboardCheck },
  { id: "estrategia", label: "Empresas", icon: Building2 },
];

const sectionTitles: Record<SectionId, string> = {
  dashboard: "Centro de Decisão",
  documentos: "Inteligência documental",
  conciliacao: "Anomalias e controlo",
  financeiro: "Análise financeira",
  inventario: "Inventário inteligente",
  ia: "IA Analista",
  nuvem: "Nuvem, histórico e pagamentos",
  estrategia: "Estratégia de escala",
};

function summarizeMovements(sourceName: string, rowsRead: number, movements: ClassifiedMovement[]): DashboardSummary {
  const sales = movements
    .filter((movement) => ["71", "72", "78"].includes(movement.accountCode))
    .reduce((sum, movement) => sum + Math.abs(movement.amount), 0);
  const expenses = movements
    .filter((movement) => ["22", "24", "31", "61", "62", "63", "68"].includes(movement.accountCode))
    .reduce((sum, movement) => sum + Math.abs(movement.amount), 0);
  const profit = sales - expenses;

  return {
    sourceName,
    rowsRead,
    sales: Number(sales.toFixed(2)),
    expenses: Number(expenses.toFixed(2)),
    profit: Number(profit.toFixed(2)),
    margin: sales > 0 ? Number(((profit / sales) * 100).toFixed(1)) : 0,
  };
}

function App() {
  const [appScreen, setAppScreen] = useState<AppScreen>("landing");
  const [activeSection, setActiveSection] = useState<SectionId>("dashboard");
  const [period, setPeriod] = useState<PeriodKey>("junho");
  const [issues, setIssues] = useState<ReconciliationIssue[]>([]);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [debts, setDebts] = useState<DebtItem[]>([]);
  const [inventorySearch, setInventorySearch] = useState("");
  const [debtFilter, setDebtFilter] = useState<"Todos" | DebtState>("Todos");
  const [classifiedMovements, setClassifiedMovements] = useState<ClassifiedMovement[]>([]);
  const [processingFile, setProcessingFile] = useState(false);
  const [refreshingOperationalState, setRefreshingOperationalState] = useState(false);
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary | null>(null);
  const [documentIntelligence, setDocumentIntelligence] = useState<DocumentIntelligence | null>(null);
  const [mfaError, setMfaError] = useState("");
  const [loginError, setLoginError] = useState("");
  const [registerError, setRegisterError] = useState("");
  const [currentAccount, setCurrentAccount] = useState<LocalAccount | null>(null);
  const [accessToken, setAccessToken] = useState("");
  const [securityChallenge, setSecurityChallenge] = useState<SecurityChallenge | null>(null);
  const [aiQuestion, setAiQuestion] = useState("");
  const [aiConversationId, setAiConversationId] = useState<string | undefined>();
  const [aiAnalysis, setAiAnalysis] = useState(() => buildAiAnalysis("Qual plataforma gera maior margem?"));
  const [aiFileAnalysis, setAiFileAnalysis] = useState<AiAnalysis | null>(null);
  const [aiGeneratedFiles, setAiGeneratedFiles] = useState<CloudFile[]>([]);
  const [aiRowErrors, setAiRowErrors] = useState<Array<{ row: number; document: string; errors: string[] }>>([]);
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [readingDocument, setReadingDocument] = useState(false);
  const [ocrError, setOcrError] = useState("");
  const [snapshotPeriod, setSnapshotPeriod] = useState<SnapshotPeriod>("daily");
  const [reportDate, setReportDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [snapshots, setSnapshots] = useState<MetricSnapshot[]>([]);
  const [snapshotComparison, setSnapshotComparison] = useState<SnapshotComparison | null>(null);
  const [billingSubscription, setBillingSubscription] = useState<BillingSubscription | null>(null);
  const [cloudFiles, setCloudFiles] = useState<CloudFile[]>([]);
  const [toast, setToast] = useState("Protótipo pronto para demonstração.");
  const onboardingFileRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    configurePersistentAudit(accessToken);
    return () => configurePersistentAudit("");
  }, [accessToken]);

  const selectedPeriod = periodData[period];
  const dashboardPeriod = dashboardSummary
    ? {
        ...selectedPeriod,
        sales: dashboardSummary.sales,
        profit: dashboardSummary.profit,
        margin: dashboardSummary.margin,
      }
    : selectedPeriod;
  const unresolvedIssues = issues.filter((issue) => issue.status !== "Resolvido");
  const activeDebts = debts.filter((debt) => debt.state !== "Pago");
  const stalledProducts = inventory.filter((item) => item.lastSaleDays > 90);
  const criticalProducts = inventory.filter((item) => item.stock <= 1);

  const filteredInventory = useMemo(() => {
    const search = inventorySearch.trim().toLowerCase();
    if (!search) return inventory;
    return inventory.filter((item) =>
      [item.ref, item.product, item.alert, item.unit, item.stockType, item.movementType, item.warehouse, item.location].some((field) => field.toLowerCase().includes(search)),
    );
  }, [inventory, inventorySearch]);

  const filteredDebts = useMemo(() => {
    if (debtFilter === "Todos") return debts;
    return debts.filter((debt) => debt.state === debtFilter);
  }, [debtFilter, debts]);

  const decisionPriorities = useMemo(
    () => buildDecisionPriorities(unresolvedIssues.length, stalledProducts.length, activeDebts.length),
    [activeDebts.length, stalledProducts.length, unresolvedIssues.length],
  );
  const platformChartData = useMemo(() => buildPlatformChartData(classifiedMovements), [classifiedMovements]);
  const monthlyChartData = useMemo(() => buildMonthlyChartData(classifiedMovements), [classifiedMovements]);

  function showToast(message: string) {
    setToast(message);
  }

  async function refreshOperationalState(token: string) {
    setRefreshingOperationalState(true);
    try {
      const [inventoryResult, debtsResult, issuesResult, filesResult, dashboardResult] = await Promise.allSettled([
        listInventoryItemsApi(token),
        listDebtItemsApi(token),
        listIssuesApi(token),
        listCloudFilesApi(token),
        getDashboardStateApi(token),
      ]);
      if (inventoryResult.status === "fulfilled") setInventory(inventoryResult.value);
      if (debtsResult.status === "fulfilled") setDebts(debtsResult.value);
      if (issuesResult.status === "fulfilled") setIssues(issuesResult.value);
      if (filesResult.status === "fulfilled") setCloudFiles(filesResult.value);
      if (dashboardResult.status === "fulfilled") {
        setDashboardSummary(dashboardResult.value.summary);
        setDocumentIntelligence(dashboardResult.value.documentIntelligence);
      }
      const loaded = [inventoryResult, debtsResult, issuesResult, filesResult, dashboardResult].filter((result) => result.status === "fulfilled").length;
      return loaded;
    } finally {
      setRefreshingOperationalState(false);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") || "").trim();
    const password = String(form.get("password") || "");

    try {
      const challenge = await authenticateAccount(email, password);
      setLoginError("");
      setMfaError("");
      setSecurityChallenge(challenge);
      setAppScreen("mfa");
      auditAction("LOGIN_STEP_1", `Credenciais validadas para ${email}.`);
      showToast("Primeira autenticação validada. Confirme o código de segurança.");
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "Email ou palavra-passe inválidos.");
      auditAction("LOGIN_FAILED", `Tentativa recusada para ${email || "email vazio"}.`);
    }
  }

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") || "").trim();
    const email = String(form.get("email") || "").trim();
    const password = String(form.get("password") || "");

    try {
      await registerClientAccount({ name, email, password });
      const challenge = await authenticateAccount(email, password);
      setRegisterError("");
      setSecurityChallenge(challenge);
      setAppScreen("mfa");
      auditAction("CLIENT_REGISTERED", `Conta cliente criada para ${email}.`);
      showToast("Conta de cliente criada. Confirme o código temporário.");
    } catch (error) {
      setRegisterError(error instanceof Error ? error.message : "Não foi possível criar a conta.");
    }
  }

  async function handleMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!securityChallenge) {
      setMfaError("Sessão de autenticação expirada. Faça login novamente.");
      setAppScreen("login");
      return;
    }

    const form = new FormData(event.currentTarget);
    const code = String(form.get("securityCode") || "").trim();

    try {
      const session = await verifySecurityCode(securityChallenge, code);
      setMfaError("");
      setAccessToken(session.accessToken);
      setCurrentAccount(session.account);
      const loadedServices = await refreshOperationalState(session.accessToken);
      setAppScreen("app");
      setActiveSection("dashboard");
      showToast(loadedServices === 5 ? "Dados operacionais atualizados." : "Acesso validado. Alguns dados serão atualizados ao abrir os módulos.");
      auditAction("MFA_SUCCESS", `Segunda autenticação validada para ${session.account.email}.`);
    } catch (error) {
      setMfaError(error instanceof Error ? error.message : "Código inválido ou expirado.");
      auditAction("MFA_FAILED", "Tentativa de segunda autenticação recusada.");
    }
  }

  async function handleOperationalFile(file: File | undefined, options?: { stayInAssistant?: boolean; signal?: AbortSignal }) {
    if (!file) return;
    if (!hasPermission(currentAccount, "files:upload")) {
      showToast("Sem permissão para carregar ficheiros operacionais.");
      auditAction("UPLOAD_BLOCKED", `Permissão recusada para ${currentAccount?.email ?? "utilizador desconhecido"}.`);
      return;
    }
    const validationError = validateUploadFile(file, OPERATIONAL_FILE_EXTENSIONS);
    if (validationError) {
      showToast(validationError);
      return;
    }
    setProcessingFile(true);
    showToast(`A analisar ${file.name}...`);
    try {
      const dataset = await buildOperationalDatasetFromFile(file, accessToken, options?.signal);
      setClassifiedMovements(dataset.classifiedMovements);
      setInventory(dataset.inventory);
      setDebts(dataset.debts);
      setIssues(dataset.issues);
      setDashboardSummary(dataset.summary);
      setDocumentIntelligence(dataset.documentIntelligence);
      setAiRowErrors(dataset.rowErrors ?? []);
      if (dataset.storedFile) {
        setCloudFiles((current) => [dataset.storedFile!, ...current.filter((item) => item.id !== dataset.storedFile!.id)]);
      }
      if (dataset.generatedFile) {
        setAiGeneratedFiles((current) => [dataset.generatedFile!, ...current.filter((item) => item.id !== dataset.generatedFile!.id)]);
        setCloudFiles((current) => [dataset.generatedFile!, ...current.filter((item) => item.id !== dataset.generatedFile!.id)]);
        const transformed = dataset.billingTransform;
        const generatedAnalysis: AiAnalysis = {
          answer: transformed
            ? `Pronto. Organizei ${transformed.includedRows} documentos válidos e separei Coimbra de Picoto em ${Object.keys(transformed.groups).length} grupos. Removi ${transformed.excludedNonBilling} documentos GT/não faturáveis e ${transformed.excludedCancelled} anulados, converti as notas de crédito em valores negativos e criei subtotais com fórmulas. O total geral ficou em ${formatCurrency(transformed.totalAmount)}. O novo Excel está disponível abaixo para descarregar.`
            : "Faturação organizada e guardada na nuvem.",
          confidence: 99,
          risk: "Baixo",
          priorities: ["Validar os subtotais", "Confirmar os documentos excluídos"],
          actions: ["Descarregar o Excel organizado", "Consultar a cópia guardada na nuvem"],
        };
        setAiAnalysis(generatedAnalysis);
        setAiFileAnalysis(generatedAnalysis);
        await downloadCloudFile(dataset.generatedFile);
      } else {
        const fileAnalysis: AiAnalysis = {
          answer: `Analisei ${dataset.summary.rowsRead} linhas de ${dataset.summary.sourceName}. Foram identificados ${dataset.documentIntelligence.stats.processed} documentos, ${dataset.documentIntelligence.stats.review} para revisão e ${dataset.documentIntelligence.stats.duplicates} possíveis duplicados. O total documental é ${formatCurrency(dataset.documentIntelligence.totals.total)}.`,
          confidence: 96,
          risk: dataset.documentIntelligence.stats.review > 0 ? "Médio" : "Baixo",
          priorities: dataset.documentIntelligence.auditTrail.slice(0, 3),
          actions: ["Rever documentos sinalizados", "Consultar os dados organizados", "Exportar o resultado"],
        };
        setAiAnalysis(fileAnalysis);
        setAiFileAnalysis(fileAnalysis);
      }
      setAppScreen("app");
      if (!options?.stayInAssistant) setActiveSection("dashboard");
      auditAction("FILE_IMPORTED", `${dataset.summary.sourceName} com ${dataset.summary.rowsRead} linhas analisadas.`);
      showToast(`IA processou ${dataset.summary.rowsRead} linhas de ${dataset.summary.sourceName}.`);
      return dataset;
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        showToast("Processamento cancelado.");
        throw error;
      }
      showToast(error instanceof Error ? error.message : "Não foi possível processar o ficheiro.");
      throw error;
    } finally {
      setProcessingFile(false);
    }
  }

  async function exportReport() {
    if (!hasPermission(currentAccount, "reports:export")) {
      showToast("Sem permissão para exportar relatórios.");
      auditAction("REPORT_EXPORT_BLOCKED", `Permissão recusada para ${currentAccount?.email ?? "utilizador desconhecido"}.`);
      return;
    }

    if (accessToken) {
      try {
        const response = await fetch(`${API_BASE_URL}/reports/executive.pdf`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!response.ok) throw new Error("Não foi possível gerar o PDF executivo.");
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "relatorio-executivo-seo.pdf";
        link.click();
        URL.revokeObjectURL(url);
        auditAction("REPORT_EXPORTED", "Relatório executivo PDF exportado.");
        showToast("Relatório PDF executivo exportado.");
        return;
      } catch (error) {
        showToast(error instanceof Error ? error.message : "A exportar CSV como alternativa.");
      }
    }

    const rows = [
      ["Indicador", "Valor"],
      ["Ficheiro analisado", dashboardSummary?.sourceName ?? "-"],
      ["Linhas analisadas", String(dashboardSummary?.rowsRead ?? 0)],
      ["Período selecionado", selectedPeriod.label],
      ["Vendas do mês", formatCurrency(dashboardPeriod.sales)],
      ["Lucro estimado", formatCurrency(dashboardPeriod.profit)],
      ["Margem média", `${dashboardPeriod.margin}%`],
      ["Produtos parados", String(stalledProducts.length)],
      ["Documentos por resolver", String(unresolvedIssues.length)],
      ["Contas ativas", String(activeDebts.length)],
    ];
    downloadCsv(`relatorio-seo-${period}.csv`, rows);
    auditAction("REPORT_EXPORTED", `Relatório executivo exportado para o período ${selectedPeriod.label}.`);
    showToast("Relatório CSV exportado.");
  }

  function exportImpact() {
    downloadCsv("impacto-antes-depois.csv", [
      ["Processo", "Antes", "Depois", "Impacto"],
      ...impactRows.map((row) => [row.process, row.before, row.after, row.impact]),
    ]);
    auditAction("IMPACT_EXPORTED", "Métricas Antes/Depois exportadas.");
    showToast("Métricas Antes/Depois exportadas.");
  }

  function downloadTemplate() {
    downloadCsv("modelo-importacao-seo.csv", [
      ["data", "descricao", "entidade", "valor", "produto", "referencia", "stock", "margem", "dias"],
      ["2026-06-01", "Venda peça automóvel", "Loja online", "245.90", "Farol LED", "SKU-001", "4", "28", "12"],
      ["2026-06-02", "Comissão marketplace Ovoko", "Ovoko", "-18.50", "Farol LED", "SKU-001", "4", "28", "12"],
      ["2026-06-03", "Saldo cliente em aberto", "Cliente A", "520.00", "", "", "", "", "35"],
    ]);
    showToast("Modelo de importação descarregado.");
  }

  async function resolveAllIssues() {
    if (!hasPermission(currentAccount, "reconciliation:write")) {
      showToast("Sem permissão para resolver pendências em massa.");
      auditAction("ISSUES_RESOLVE_BLOCKED", `Permissão recusada para ${currentAccount?.email ?? "utilizador desconhecido"}.`);
      return;
    }
    try {
      const updatedIssues = await resolveAllIssuesApi(accessToken);
      setIssues(updatedIssues);
      auditAction("ISSUES_RESOLVED", "Todas as pendências de conciliação foram marcadas como resolvidas.");
      showToast("Todos os problemas de conciliação foram marcados como resolvidos.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível resolver as pendências.");
    }
  }

  async function resolveIssue(id: number) {
    if (!hasPermission(currentAccount, "reconciliation:write")) {
      showToast("Sem permissão para resolver pendências.");
      auditAction("ISSUE_RESOLVE_BLOCKED", `Permissão recusada para ${currentAccount?.email ?? "utilizador desconhecido"}.`);
      return;
    }
    try {
      const updatedIssue = await resolveIssueApi(accessToken, id);
      setIssues((current) => current.map((issue) => (issue.id === id ? updatedIssue : issue)));
      auditAction("ISSUE_RESOLVED", `Pendência ${id} marcada como resolvida.`);
      showToast("Problema marcado como resolvido.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível resolver a pendência.");
    }
  }

  async function handleImport(file: File | undefined) {
    if (!file) return;
    if (!hasPermission(currentAccount, "reconciliation:write")) {
      showToast("Sem permissão para importar conciliações.");
      auditAction("RECONCILIATION_IMPORT_BLOCKED", `Permissão recusada para ${currentAccount?.email ?? "utilizador desconhecido"}.`);
      return;
    }
    const validationError = validateUploadFile(file, TEXT_FILE_EXTENSIONS);
    if (validationError) {
      showToast(validationError);
      return;
    }
    try {
      const updatedIssues = await importReconciliationApi(accessToken, file);
      setIssues(updatedIssues);
      auditAction("RECONCILIATION_IMPORTED", `${file.name} importado para validação no backend.`);
      showToast(`${updatedIssues.length} pendências disponíveis após importação.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível importar a conciliação.");
    }
  }

  async function registerSale(ref: string) {
    if (!hasPermission(currentAccount, "inventory:write")) {
      showToast("Sem permissão para alterar inventário.");
      auditAction("INVENTORY_MOVEMENT_BLOCKED", `Permissão recusada para ${currentAccount?.email ?? "utilizador desconhecido"}.`);
      return;
    }
    try {
      const updatedItem = await registerInventorySaleApi(accessToken, ref);
      setInventory((current) => current.map((item) => (item.ref === ref ? updatedItem : item)));
      auditAction("INVENTORY_MOVEMENT", `Saída de stock registada para a referência ${ref}.`);
      showToast("Saída de stock registada.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível registar a saída de stock.");
    }
  }

  async function markPaid(id: number) {
    if (!hasPermission(currentAccount, "finance:write")) {
      showToast("Sem permissão para alterar contas correntes.");
      auditAction("DEBT_MARK_PAID_BLOCKED", `Permissão recusada para ${currentAccount?.email ?? "utilizador desconhecido"}.`);
      return;
    }
    try {
      const updatedDebt = await markDebtPaidApi(accessToken, id);
      setDebts((current) => current.map((debt) => (debt.id === id ? updatedDebt : debt)));
      auditAction("DEBT_MARKED_PAID", `Conta corrente ${id} marcada como paga.`);
      showToast("Conta corrente marcada como paga.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível marcar a conta como paga.");
    }
  }

  async function askAi(questionOverride?: string, analysisLevel = "Elevado") {
    const submittedQuestion = (questionOverride ?? aiQuestion).trim();
    if (!submittedQuestion) return;
    try {
      const analysis = accessToken ? await askBackendAi(accessToken, submittedQuestion, aiConversationId, analysisLevel) : buildAiAnalysis(submittedQuestion);
      setAiAnalysis(analysis);
      if (analysis.conversationId) setAiConversationId(analysis.conversationId);
      showToast(accessToken ? "IA Analista atualizada com dados reais da empresa." : "IA Analista atualizada.");
      return analysis;
    } catch (error) {
      if (!accessToken) {
        const analysis = buildAiAnalysis(submittedQuestion);
        setAiAnalysis(analysis);
        return analysis;
      }
      showToast(error instanceof Error ? error.message : "Não foi possível consultar a IA com dados reais.");
      throw error;
    }
  }

  async function handleReadDocument(file: File) {
    if (!accessToken || !currentAccount?.companyId) {
      setOcrError("Inicie sessão para ler documentos.");
      return;
    }
    setReadingDocument(true);
    setOcrError("");
    try {
      const result = await readDocumentOcr(accessToken, currentAccount.companyId, file);
      setOcrResult(result);
      showToast(`${result.page_count} página(s) lida(s) de ${result.filename}.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Não foi possível ler o documento.";
      setOcrError(message);
      showToast(message);
    } finally {
      setReadingDocument(false);
    }
  }

  async function refreshCloudState(periodOverride = snapshotPeriod, dateOverride = reportDate) {
    if (!accessToken) return;
    const [history, comparison, subscription, files] = await Promise.allSettled([
        listMetricSnapshotsApi(accessToken, periodOverride, periodOverride === "daily" ? dateOverride : undefined),
        compareMetricSnapshotsApi(accessToken, periodOverride),
        getBillingSubscriptionApi(accessToken),
        listCloudFilesApi(accessToken),
    ]);
    if (history.status === "fulfilled") setSnapshots(history.value);
    if (comparison.status === "fulfilled") setSnapshotComparison(comparison.value);
    if (subscription.status === "fulfilled") setBillingSubscription(subscription.value);
    if (files.status === "fulfilled") setCloudFiles(files.value);
    const failed = [history, comparison, subscription, files].filter((result) => result.status === "rejected").length;
    showToast(failed ? `Nuvem atualizada parcialmente; ${failed} serviço(s) indisponível(eis).` : "Arquivo, histórico e faturação atualizados.");
  }

  useEffect(() => {
    if (activeSection === "nuvem" && accessToken) void refreshCloudState();
  }, [activeSection, accessToken]);

  async function createSnapshot(periodToCreate = snapshotPeriod, dateToCreate = reportDate) {
    if (!hasPermission(currentAccount, "reports:export")) {
      showToast("Sem permissão para criar snapshots comparáveis.");
      return;
    }
    try {
      await createMetricSnapshotApi(accessToken, periodToCreate, `${currentAccount?.companyName ?? "Empresa"} · ${dateToCreate}`, dateToCreate);
      await refreshCloudState(periodToCreate, dateToCreate);
      auditAction("SNAPSHOT_CREATED", `Snapshot ${periodToCreate} guardado para comparação.`);
      showToast("Snapshot guardado para comparação futura.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível guardar o snapshot.");
    }
  }

  async function startCheckout(plan: string) {
    if (!hasPermission(currentAccount, "billing:manage")) {
      showToast("Sem permissão para gerir pagamentos.");
      return;
    }
    try {
      const checkout = await createBillingCheckoutApi(accessToken, plan);
      window.location.href = checkout.checkoutUrl;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível abrir o pagamento.");
    }
  }

  async function downloadCloudFile(file: CloudFile) {
    try {
      const response = await fetch(`${API_BASE_URL}/cloud/files/${encodeURIComponent(file.id)}/download`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) throw new Error("Não foi possível descarregar o ficheiro guardado.");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = file.filename;
      link.click();
      URL.revokeObjectURL(url);
      showToast(`${file.filename} descarregado da nuvem.`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Não foi possível descarregar o ficheiro.");
    }
  }

  if (appScreen === "landing") {
    return <ProductShowcaseLanding onLogin={() => setAppScreen("login")} onRegister={() => setAppScreen("register")} />;
  }

  if (appScreen === "login") {
    return (
      <MinimalLoginPage
        error={loginError}
        onSubmit={handleLogin}
        onBack={() => setAppScreen("landing")}
        onRegister={() => setAppScreen("register")}
      />
    );
  }

  if (appScreen === "register") {
    return (
      <RegisterPage
        error={registerError}
        onSubmit={handleRegister}
        onBack={() => setAppScreen("landing")}
        onLogin={() => setAppScreen("login")}
      />
    );
  }

  if (appScreen === "mfa") {
    return <MfaPage error={mfaError} challenge={securityChallenge} onSubmit={handleMfa} onBack={() => setAppScreen("login")} />;
  }

  return (
    <div className="min-h-screen bg-[#030607] text-[#f8fafc]">
      <input
        ref={onboardingFileRef}
        className="hidden"
        type="file"
        accept=".xlsx,.pdf,.csv,.txt,.xml,.jpg,.jpeg,.png"
        disabled={processingFile}
        onChange={(event) => {
          void handleOperationalFile(event.target.files?.[0]);
          event.currentTarget.value = "";
        }}
      />
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-white/10 bg-[#030607] text-[#f8fafc] lg:block">
        <div className="flex h-full flex-col">
          <div className="border-b border-white/10 px-5 py-5">
            <button
              className="block text-left transition hover:scale-[1.01]"
              onClick={() => setAppScreen("landing")}
              title="Voltar à página inicial"
              type="button"
            >
              <SeoWordmark variant="dark" size="header" />
              <p className="mt-2 text-xs text-[#9c8276]">Eficiência Operacional</p>
            </button>
          </div>

          <nav className="flex-1 space-y-1 px-4 py-6" aria-label="Navegação principal">
            {navItems.map((item) => (
              <NavButton
              key={`${item.id}-${item.label}`}
                item={item}
                active={item.id === activeSection}
                onClick={() => setActiveSection(item.id)}
              />
            ))}
          </nav>

          <div className="border-t border-white/10 px-7 py-5">
            <p className="text-xs uppercase tracking-[0.16em] text-[#6e6e73]">Estado do MVP</p>
            <p className="mt-2 text-sm leading-5 text-[#c7b0a5]" aria-live="polite">{toast}</p>
          </div>
        </div>
      </aside>

      <main className="lg:pl-64">
        <header className={`border-b border-white/10 bg-[#030607]/90 backdrop-blur-xl ${activeSection === "dashboard" ? "h-12" : ""}`}>
          <div className={activeSection === "dashboard" ? "hidden" : "mx-auto flex max-w-7xl flex-col gap-5 px-5 py-5 lg:px-8"}>
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#a38476]">
                  {currentAccount?.companyName ?? "Empresa"} · Controlo operacional
                </p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white md:text-4xl">
                  {sectionTitles[activeSection]}
                </h2>
                {currentAccount && (
                  <p className="mt-2 text-sm text-[#9c8276]">
                    {currentAccount.role === "admin" ? "Administrador" : "Cliente"} · {currentAccount.name} · {currentAccount.companyName}
                  </p>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <label className="sr-only" htmlFor="period">
                  Período
                </label>
                <select
                  id="period"
                  className="h-10 rounded-full border border-black/10 bg-white px-4 text-sm text-[#1d1d1f] shadow-[0_8px_30px_rgba(0,0,0,0.04)]"
                  value={period}
                  onChange={(event) => setPeriod(event.target.value as PeriodKey)}
                >
                  {Object.entries(periodData).map(([key, data]) => (
                    <option key={key} value={key}>
                      {data.label}
                    </option>
                  ))}
                </select>
                <button
                  className="inline-flex h-10 items-center gap-2 rounded-full bg-[#0071e3] px-5 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(0,113,227,0.18)] hover:bg-[#0077ed]"
                  onClick={exportReport}
                  type="button"
                >
                  <Download size={17} aria-hidden="true" />
                  Relatório
                </button>
              </div>
            </div>

            <div className="grid gap-2 sm:grid-cols-3 lg:hidden">
              {navItems.map((item) => (
                <NavButton
                  key={`${item.id}-${item.label}`}
                  item={item}
                  active={item.id === activeSection}
                  onClick={() => setActiveSection(item.id)}
                  compact
                />
              ))}
            </div>
          </div>
        </header>

        <div className="hidden">
          {[
            ["1", "Dados carregados", dashboardSummary ? `${dashboardSummary.rowsRead} linhas analisadas` : "ficheiro analisado"],
            ["2", "Decisão gerada", `${decisionPriorities.length} prioridades ativas`],
            ["3", "Próximo passo", "Exportar PDF ou resolver alertas"],
          ].map(([step, title, detail]) => (
            <div key={step} className="flex items-center gap-3 rounded-2xl bg-[#f5f5f7] px-4 py-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0071e3] text-sm font-semibold text-white">{step}</span>
              <div>
                <p className="text-sm font-semibold text-[#1d1d1f]">{title}</p>
                <p className="text-xs text-[#6e6e73]">{detail}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mx-auto max-w-[1480px] space-y-7 px-5 py-7 lg:px-8">
          {activeSection === "dashboard" && (
            <OperationalHomeView
              summary={dashboardSummary}
              intelligence={documentIntelligence}
              inventory={inventory}
              debts={debts}
              issues={issues}
              cloudFiles={cloudFiles}
              processingFile={processingFile}
              refreshing={refreshingOperationalState}
              onGoTo={setActiveSection}
              onUpload={() => onboardingFileRef.current?.click()}
              onRefresh={() => void refreshOperationalState(accessToken)}
            />
          )}

          {activeSection === "conciliacao" && (
            <ReconciliationView
              fileInputRef={fileInputRef}
              issues={issues}
              onImport={handleImport}
              onResolveAll={resolveAllIssues}
              onResolveIssue={resolveIssue}
            />
          )}

          {activeSection === "financeiro" && (
            <FinanceView
              debts={filteredDebts}
              summary={dashboardPeriod}
              movements={classifiedMovements}
              debtFilter={debtFilter}
              onFilterChange={setDebtFilter}
              onMarkPaid={markPaid}
              onExport={() => {
                downloadCsv("contas-correntes.csv", [
                  ["Fatura", "Entidade", "Tipo", "Emissão", "Vencimento", "Valor", "Prazo", "Estado"],
                  ...debts.map((debt) => [
                    debt.invoice,
                    debt.entity,
                    debt.type,
                    debt.issueDate,
                    debt.dueDate,
                    formatCurrency(debt.amount),
                    `${debt.dueDays} dias`,
                    debt.state,
                  ]),
                ]);
                showToast("Contas correntes exportadas.");
              }}
            />
          )}

          {activeSection === "inventario" && (
            <InventoryView
              inventory={filteredInventory}
              search={inventorySearch}
              onSearchChange={setInventorySearch}
              onRegisterSale={registerSale}
              onExport={() => {
                downloadCsv("inventario-seo.csv", [
                  ["Referência", "Produto", "Unidade", "Tipo", "Movimento", "Qtd. movimento", "Armazém", "Sistema", "Físico", "Diferença", "Custo", "Valor stock", "Localização", "Confiança", "Estado", "Alerta"],
                  ...inventory.map((item) => [
                    item.ref,
                    item.product,
                    item.unit,
                    item.stockType,
                    item.movementType,
                    String(item.movementQuantity),
                    item.warehouse,
                    String(item.systemQuantity),
                    String(item.physicalQuantity),
                    String(item.differenceQuantity),
                    String(item.unitCost),
                    String(item.stockValue),
                    item.location,
                    `${item.confidence}%`,
                    item.validationState,
                    item.alert,
                  ]),
                ]);
                showToast("Inventário exportado.");
              }}
            />
          )}

          {activeSection === "ia" && (
            <AiView
              question={aiQuestion}
              analysis={aiAnalysis}
              onQuestionChange={setAiQuestion}
              onAsk={askAi}
              onAttach={(file, signal) => handleOperationalFile(file, { stayInAssistant: true, signal })}
              generatedFiles={aiGeneratedFiles}
              rowErrors={aiRowErrors}
              onDownloadGeneratedFile={downloadCloudFile}
              onNewConversation={() => { setAiConversationId(undefined); setAiFileAnalysis(null); setAiRowErrors([]); }}
            />
          )}

          {activeSection === "documentos" && (
            <DocumentIntelligenceView
              intelligence={documentIntelligence}
              onUpload={() => onboardingFileRef.current?.click()}
              onOpenIssues={() => setActiveSection("conciliacao")}
              ocrResult={ocrResult}
              readingDocument={readingDocument}
              ocrError={ocrError}
              onReadDocument={handleReadDocument}
            />
          )}

          {activeSection === "nuvem" && (
            <CloudBillingView
              period={snapshotPeriod}
              reportDate={reportDate}
              snapshots={snapshots}
              comparison={snapshotComparison}
              subscription={billingSubscription}
              files={cloudFiles}
              onPeriodChange={(nextPeriod) => {
                setSnapshotPeriod(nextPeriod);
                void refreshCloudState(nextPeriod, reportDate);
              }}
              onReportDateChange={(nextDate) => {
                setReportDate(nextDate);
                setSnapshotPeriod("daily");
                void refreshCloudState("daily", nextDate);
              }}
              onRefresh={() => refreshCloudState()}
              onCreateSnapshot={() => createSnapshot("daily", reportDate)}
              onCheckout={startCheckout}
              onDownloadFile={downloadCloudFile}
            />
          )}

          {activeSection === "estrategia" && (
            <StrategyExecutionView
              unresolvedIssues={unresolvedIssues.length}
              stalledProducts={stalledProducts.length}
              activeDebts={activeDebts.length}
              snapshotsCount={snapshots.length}
              summary={dashboardPeriod}
              onGoTo={setActiveSection}
            />
          )}
        </div>
      </main>
    </div>
  );
}

function OperationalHomeView({
  summary,
  intelligence,
  inventory,
  debts,
  issues,
  cloudFiles,
  processingFile,
  refreshing,
  onGoTo,
  onUpload,
  onRefresh,
}: {
  summary: DashboardSummary | null;
  intelligence: DocumentIntelligence | null;
  inventory: InventoryItem[];
  debts: DebtItem[];
  issues: ReconciliationIssue[];
  cloudFiles: CloudFile[];
  processingFile: boolean;
  refreshing: boolean;
  onGoTo: (section: SectionId) => void;
  onUpload: () => void;
  onRefresh: () => void;
}) {
  const documents = intelligence?.documents ?? [];
  const unresolved = issues.filter((issue) => issue.status !== "Resolvido");
  const openDebts = debts.filter((debt) => debt.state !== "Pago");
  const overdueDebts = debts.filter((debt) => debt.state === "Em atraso");
  const totalStock = inventory.reduce((sum, item) => sum + item.physicalQuantity, 0);
  const stockValue = inventory.reduce((sum, item) => sum + item.stockValue, 0);
  const divergences = inventory.filter((item) => item.differenceQuantity !== 0).length;
  const criticalStock = inventory.filter((item) => item.physicalQuantity <= 1).length;
  const openDebtValue = openDebts.reduce((sum, debt) => sum + debt.amount, 0);
  const overdueValue = overdueDebts.reduce((sum, debt) => sum + debt.amount, 0);
  const documentCount = intelligence?.stats.processed ?? summary?.rowsRead ?? 0;
  const invoices = documents.filter((item) => item.documentType === "Fatura").length;
  const receipts = documents.filter((item) => item.documentType === "Fatura-recibo").length;
  const credits = documents.filter((item) => item.documentType === "Nota de crédito").length;
  const totalBilling = intelligence?.totals.total ?? summary?.sales ?? 0;
  const capitalAtRisk = overdueValue + inventory.filter((item) => item.differenceQuantity !== 0).reduce((sum, item) => sum + Math.abs(item.differenceQuantity * item.unitCost), 0);
  const controlled = issues.length ? Math.round(((issues.length - unresolved.length) / issues.length) * 100) : 100;
  const healthScore = calculateOperationalScore({
    totalIssues: issues.length,
    unresolvedIssues: unresolved.length,
    totalDebts: debts.length,
    overdueDebts: overdueDebts.length,
    totalInventory: inventory.length,
    inventoryDivergences: divergences,
    criticalStock,
    stalledProducts: inventory.filter((item) => item.lastSaleDays > 90).length,
  }).score;
  const latestFile = cloudFiles[0];
  const hasOperationalData = Boolean(documentCount || inventory.length || debts.length || issues.length || cloudFiles.length);
  const cardClass = "rounded-2xl border border-white/10 bg-[#080c0e] p-5 transition hover:-translate-y-0.5 hover:border-amber-400/30";
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Bom dia" : hour < 20 ? "Boa tarde" : "Boa noite";
  const metricCards: Array<[string, string, string, LucideIcon, string, SectionId]> = [
    ["Faturação analisada", formatCurrency(totalBilling), `${documentCount} documentos`, Euro, "text-amber-400", "documentos"],
    ["Pagamentos em aberto", formatCurrency(openDebtValue), `${overdueDebts.length} vencidos`, WalletCards, overdueDebts.length ? "text-red-300" : "text-emerald-400", "financeiro"],
    ["Valor de inventário", formatCurrency(stockValue), `${totalStock} unidades · ${criticalStock} críticas`, Boxes, "text-emerald-400", "inventario"],
    ["Anomalias abertas", String(unresolved.length), `${controlled}% controladas`, AlertTriangle, unresolved.length ? "text-orange-300" : "text-emerald-400", "conciliacao"],
  ];
  const quickActions: Array<[string, string, LucideIcon, () => void, string]> = [
    [processingFile ? "A analisar ficheiro..." : "Analisar novo ficheiro", processingFile ? "Aguarde enquanto os dados são validados" : "Excel, CSV, PDF, imagem ou XML", Upload, onUpload, "border-blue-400/25 bg-blue-500/[0.07]"],
    ["Perguntar à IA", "Obter resposta com os dados da empresa", Bot, () => onGoTo("ia"), "border-amber-400/25 bg-amber-500/[0.07]"],
    ["Resolver anomalias", `${unresolved.length} ocorrências aguardam validação`, AlertTriangle, () => onGoTo("conciliacao"), "border-orange-400/25 bg-orange-500/[0.07]"],
    ["Consultar histórico", `${cloudFiles.length} ficheiros guardados`, Cloud, () => onGoTo("nuvem"), "border-emerald-400/25 bg-emerald-500/[0.07]"],
  ];
  const priority = unresolved.length
    ? { title: `Validar ${unresolved.length} anomalia(s) antes do relatório`, detail: `${formatCurrency(capitalAtRisk)} estão associados a pagamentos vencidos e diferenças de inventário.`, action: "Abrir anomalias", target: "conciliacao" as SectionId, tone: "text-orange-300" }
    : overdueDebts.length
      ? { title: `Acompanhar ${overdueDebts.length} pagamento(s) vencido(s)`, detail: `${formatCurrency(overdueValue)} aguardam regularização.`, action: "Ver pagamentos", target: "financeiro" as SectionId, tone: "text-red-300" }
      : { title: "Operação sem bloqueios críticos", detail: "Os principais indicadores estão controlados. Continue a importar os dados diariamente.", action: "Analisar ficheiro", target: "documentos" as SectionId, tone: "text-emerald-300" };

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-white/10 bg-[radial-gradient(circle_at_85%_10%,rgba(245,158,11,0.13),transparent_35%),linear-gradient(135deg,#0b1013,#050708)] p-6 md:p-8">
        <div className="grid gap-7 xl:grid-cols-[1.25fr_0.75fr] xl:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs font-semibold text-emerald-300">
                <span className="h-2 w-2 rounded-full bg-emerald-400" /> Dados sincronizados
              </span>
              <span className="text-xs text-[#9c8276]">Atualizado agora · {summary?.sourceName ?? latestFile?.filename ?? "sem ficheiro recente"}</span>
              <button
                className="rounded-full border border-white/10 px-3 py-1.5 text-xs font-semibold text-white transition hover:border-white/25 hover:bg-white/5 disabled:cursor-wait disabled:opacity-50"
                disabled={refreshing}
                onClick={onRefresh}
                type="button"
              >
                {refreshing ? "A atualizar..." : "Atualizar dados"}
              </button>
            </div>
            <p className="mt-6 text-xs uppercase tracking-[0.2em] text-[#a38476]">Centro operacional</p>
            <h1 className="mt-2 max-w-3xl text-3xl font-semibold tracking-tight text-white md:text-5xl">{greeting}. Esta é a situação atual da empresa.</h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-[#b69b8e]">
              Informação consolidada de faturação, pagamentos, inventário, documentos e anomalias.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/25 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-[#9c8276]">Índice operacional</p>
                <p className={`mt-2 text-4xl font-semibold ${healthScore >= 80 ? "text-emerald-300" : healthScore >= 55 ? "text-amber-300" : "text-red-300"}`}>{healthScore}<span className="text-lg text-white/35">/100</span></p>
              </div>
              <ShieldCheck size={34} className="text-amber-400" />
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-amber-400 to-emerald-400" style={{ width: `${healthScore}%` }} /></div>
            <p className="mt-3 text-xs text-[#9c8276]">
              {hasOperationalData ? "Meta: 90 ou mais. Resolva anomalias e divergências para aproximar o índice de 100." : "Carregue um ficheiro para calcular o índice real."}
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metricCards.map(([label, value, detail, Icon, tone, target]) => (
          <button key={label} className={`${cardClass} text-left`} onClick={() => onGoTo(target)} type="button">
            <div className="flex items-center justify-between text-xs text-[#a38476]"><span>{label}</span><Icon size={17} /></div>
            <p className={`mt-4 text-3xl font-semibold ${tone}`}>{String(value)}</p>
            <p className="mt-1 text-sm text-[#9c8276]">{String(detail)}</p>
          </button>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-6">
          <p className="text-xs uppercase tracking-[0.18em] text-[#a38476]">Prioridade recomendada</p>
          <div className="mt-5 flex items-start gap-4">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-400/10 text-amber-400"><Target size={22} /></span>
            <div>
              <h2 className={`text-xl font-semibold ${priority.tone}`}>{priority.title}</h2>
              <p className="mt-2 text-sm leading-6 text-[#9c8276]">{priority.detail}</p>
              <button className="mt-5 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-black hover:bg-amber-100" onClick={() => priority.target === "documentos" ? onUpload() : onGoTo(priority.target)} type="button">{priority.action}</button>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-6">
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-[0.18em] text-[#a38476]">Qualidade dos dados</p>
            <span className="text-sm font-semibold text-white">{controlled}%</span>
          </div>
          <div className="mt-5 space-y-4">
            {[
              ["Documentos válidos", intelligence?.stats.processed ? Math.round((intelligence.stats.valid / intelligence.stats.processed) * 100) : 100, `${intelligence?.stats.review ?? 0} para revisão`],
              ["Conciliação", controlled, `${unresolved.length} anomalias abertas`],
              ["Inventário conciliado", inventory.length ? Math.round(((inventory.length - divergences) / inventory.length) * 100) : 100, `${divergences} divergências`],
            ].map(([label, percentage, detail]) => (
              <div key={String(label)}>
                <div className="flex justify-between text-sm"><span className="text-white">{String(label)}</span><span className="text-[#9c8276]">{String(detail)}</span></div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-amber-400" style={{ width: `${Number(percentage)}%` }} /></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section>
        <p className="mb-3 text-xs uppercase tracking-[0.18em] text-[#a38476]">Ações rápidas</p>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {quickActions.map(([label, detail, Icon, action, style]) => (
            <button key={label} type="button" disabled={processingFile && label === "A analisar ficheiro..."} onClick={action} className={`rounded-2xl border p-5 text-left transition hover:-translate-y-0.5 disabled:cursor-wait disabled:opacity-60 ${style}`}>
              <Icon size={19} className="text-white" />
              <p className="mt-4 font-semibold text-white">{label}</p>
              <p className="mt-1 text-sm text-[#9c8276]">{detail}</p>
            </button>
          ))}
        </div>
      </section>

      <section className={cardClass}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[#a38476]">Resumo dos dados atuais</p>
            <p className="mt-2 text-sm text-[#9c8276]">{latestFile ? `Último ficheiro: ${latestFile.filename}` : "Sem ficheiros guardados no histórico."}</p>
          </div>
          <button className="rounded-xl border border-white/10 px-4 py-2 text-sm font-semibold text-white hover:bg-white/5" onClick={() => onGoTo("nuvem")} type="button">Ver histórico</button>
        </div>
        <div className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-6">
          {[
            ["Faturas", invoices, "text-blue-400"],
            ["Faturas-recibo", receipts, "text-indigo-400"],
            ["Notas de crédito", credits, "text-fuchsia-400"],
            ["Duplicados", intelligence?.stats.duplicates ?? 0, "text-orange-300"],
            ["Pagamentos vencidos", overdueDebts.length, "text-red-300"],
            ["Stock crítico", criticalStock, "text-emerald-300"],
          ].map(([label, value, tone]) => (
            <div key={String(label)} className="border-white/10 xl:border-r xl:last:border-0">
              <p className="text-xs leading-5 text-[#a38476]">{String(label)}</p><p className={`mt-2 text-2xl font-semibold ${tone}`}>{String(value)}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function DashboardView({
  selectedPeriod,
  unresolvedIssues,
  stalledProducts,
  activeDebts,
  onGoTo,
  onExportImpact,
  onExportReport,
  onResolveAll,
  priorities,
  platformChartData,
  monthlyChartData,
}: {
  selectedPeriod: (typeof periodData)[keyof typeof periodData];
  unresolvedIssues: number;
  stalledProducts: number;
  activeDebts: number;
  onGoTo: (section: SectionId) => void;
  onExportImpact: () => void;
  onExportReport: () => void;
  onResolveAll: () => void;
  priorities: DecisionPriority[];
  platformChartData: Array<{ name: string; receita: number; margem: number }>;
  monthlyChartData: Array<{ month: string; vendas: number; margem: number }>;
}) {
  const potentialScore = priorities.reduce((sum, priority) => sum + Math.max(priority.score, 0), 0);
  const riskLevel = unresolvedIssues + activeDebts > 8 ? "Elevado" : unresolvedIssues > 0 ? "Moderado" : "Baixo";
  const seoScore = calculateSeoIndex(selectedPeriod.margin, unresolvedIssues, stalledProducts, activeDebts);
  const capitalAtRisk = activeDebts * 190 + stalledProducts * 75 + unresolvedIssues * 320;
  const dailyActions = buildDailyDecisionActions(unresolvedIssues, stalledProducts, activeDebts, selectedPeriod);
  const topAction = dailyActions[0];
  const openActions = dailyActions.filter((action) => !action.done);
  const protectedValue = dailyActions.reduce((sum, action) => sum + action.impactValue, 0);

  return (
    <>
      <section className="overflow-hidden rounded-[32px] bg-white shadow-[0_24px_80px_rgba(0,0,0,0.08)]">
        <div className="border-b border-black/5 bg-[#fbfbfd] px-5 py-7 md:px-7">
          <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
            <div className="max-w-4xl">
              <div className="inline-flex items-center gap-2 rounded-full bg-[#f5f5f7] px-4 py-2 text-sm font-semibold text-[#0071e3]">
                <BrainCircuit size={16} aria-hidden="true" />
                Comando diário SEO Core
              </div>
              <h3 className="mt-4 text-3xl font-semibold tracking-tight text-[#1d1d1f] md:text-4xl">
                {topAction.done ? "Operação pronta para acompanhar" : topAction.title}
              </h3>
              <p className="mt-3 text-sm leading-6 text-[#6e6e73] md:text-base">
                {topAction.done
                  ? "Os principais sinais estão controlados. Continue a guardar histórico, comparar períodos e procurar novas perdas escondidas."
                  : topAction.recommendation}
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  className="inline-flex h-11 items-center gap-2 rounded-full bg-[#0071e3] px-5 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(0,113,227,0.18)] hover:bg-[#0077ed]"
                  onClick={() => {
                    onGoTo(topAction.target);
                  }}
                  type="button"
                >
                  <Target size={17} aria-hidden="true" />
                  {topAction.cta}
                </button>
                <button
                  className="inline-flex h-11 items-center gap-2 rounded-full border border-black/10 bg-white px-5 text-sm font-semibold text-[#1d1d1f] hover:bg-[#f5f5f7]"
                  onClick={onExportReport}
                  type="button"
                >
                  <Download size={17} aria-hidden="true" />
                  Exportar decisão
                </button>
              </div>
            </div>
            <div className="rounded-[28px] bg-[#1d1d1f] p-5 text-white">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-white/60">Dinheiro em risco hoje</p>
              <p className="mt-3 text-4xl font-semibold">{formatCurrency(capitalAtRisk)}</p>
              <p className="mt-2 text-sm text-white/70">
                {openActions.length} ações abertas podem recuperar até {potentialScore} pontos SEO.
              </p>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-white/10 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-white/55">Índice</p>
                  <p className="mt-2 text-2xl font-semibold">{seoScore}/100</p>
                </div>
                <div className="rounded-2xl bg-white/10 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-white/55">Risco</p>
                  <p className="mt-2 text-2xl font-semibold">{riskLevel}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-2 border-b border-black/5 bg-white px-5 py-4 md:grid-cols-5 md:px-6">
          {[
            ["Resolver tudo", () => onResolveAll()],
            ["Exportar PDF executivo", () => onExportReport()],
            ["Validar contas", () => onGoTo("financeiro" as SectionId)],
            ["Atualizar stock", () => onGoTo("inventario" as SectionId)],
            ["Gerar plano de ação", () => onGoTo("ia" as SectionId)],
          ].map(([label, action]) => (
            <button
              key={String(label)}
              className="rounded-full border border-black/10 bg-[#f5f5f7] px-4 py-2.5 text-sm font-semibold text-[#1d1d1f] hover:bg-white"
              onClick={action as () => void}
              type="button"
            >
              {String(label)}
            </button>
          ))}
        </div>

        <div className="grid gap-3 border-b border-black/5 bg-[#fbfbfd] px-5 py-5 md:grid-cols-4 md:px-6">
          <DecisionAnswer
            label="Decisão principal"
            value={topAction.shortTitle}
            detail={topAction.reason}
          />
          <DecisionAnswer
            label="Valor protegível"
            value={formatCurrency(protectedValue)}
            detail="estimativa das ações abertas"
          />
          <DecisionAnswer
            label="Ações abertas"
            value={String(openActions.length)}
            detail={`${dailyActions.length - openActions.length} já controladas`}
          />
          <DecisionAnswer
            label="Tempo para começar"
            value={topAction.timeToStart}
            detail="primeiro passo prático"
          />
        </div>

        <div className="grid gap-4 bg-white p-5 md:p-6 xl:grid-cols-3">
          {dailyActions.map((action) => (
            <DailyDecisionCard
              key={action.title}
              action={action}
              onAction={() => {
                onGoTo(action.target);
              }}
            />
          ))}
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Indicadores principais">
        <MetricCard
          icon={ArrowUpRight}
          label="Vendas do mês"
          value={formatCurrency(selectedPeriod.sales)}
          delta="+8,2%"
          tone="success"
        />
        <MetricCard
          icon={BarChart3}
          label="Lucro estimado"
          value={formatCurrency(selectedPeriod.profit)}
          delta={`${selectedPeriod.margin}% margem`}
          tone="navy"
        />
        <MetricCard
          icon={PackageSearch}
          label="Produtos parados"
          value={String(stalledProducts)}
          delta="mais de 90 dias"
          tone="warning"
        />
        <MetricCard
          icon={AlertTriangle}
          label="Tarefas críticas"
          value={String(unresolvedIssues + activeDebts)}
          delta={`${unresolvedIssues} conciliações`}
          tone="danger"
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.95fr]">
        <Panel title="Comparação por plataforma" action="Ver módulo" onAction={() => onGoTo("financeiro")}>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={platformChartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E6EDF5" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={12} />
                <Tooltip
                  cursor={{ fill: "rgba(16, 43, 74, 0.06)" }}
                  formatter={(value, name) => [
                    name === "receita" ? `${value} EUR` : `${value}%`,
                    name === "receita" ? "Receita" : "Margem",
                  ]}
                />
                <Bar dataKey="receita" radius={[6, 6, 0, 0]}>
                  {platformChartData.map((entry, index) => (
                    <Cell key={entry.name} fill={["#102B4A", "#0E9F6E", "#B7791F", "#2563EB"][index]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Alertas operacionais" action="Resolver todos" onAction={onResolveAll}>
          <div className="space-y-3">
            <AlertRow
              icon={AlertTriangle}
              title="Contas e documentos"
              detail={`${activeDebts} contas exigem acompanhamento antes do fecho mensal.`}
              tone="danger"
            />
            <AlertRow
              icon={PackageSearch}
              title="Produtos parados"
              detail={`${stalledProducts} referências estão sem movimento há mais de 90 dias.`}
              tone="warning"
            />
            <AlertRow
              icon={ShieldCheck}
              title="Conciliação"
              detail={`${unresolvedIssues} problemas continuam por resolver.`}
              tone="success"
            />
          </div>
        </Panel>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <Panel title="Evolução mensal" action="Ver análise" onAction={() => onGoTo("financeiro")}>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthlyChartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E6EDF5" />
                <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis tickLine={false} axisLine={false} fontSize={12} />
                <Tooltip />
                <Line type="monotone" dataKey="vendas" stroke="#102B4A" strokeWidth={3} dot={false} />
                <Line type="monotone" dataKey="margem" stroke="#0E9F6E" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Impacto Antes/Depois" action="Exportar" onAction={onExportImpact}>
          <DataTable
            columns={["Processo", "Antes", "Depois", "Impacto"]}
            rows={impactRows.map((row) => [row.process, row.before, row.after, row.impact])}
          />
        </Panel>
      </section>
    </>
  );
}

function calculateSeoIndex(margin: number, unresolvedIssues: number, stalledProducts: number, activeDebts: number) {
  const marginBonus = margin >= 20 ? 4 : margin > 0 ? Math.max(0, Math.round((margin - 10) / 3)) : 0;
  const riskPenalty =
    Math.min(12, unresolvedIssues) +
    Math.min(10, stalledProducts) +
    Math.min(10, Math.round(activeDebts * 1.25));
  return Math.max(60, Math.min(100, 96 + marginBonus - riskPenalty));
}

type DailyDecisionAction = {
  title: string;
  shortTitle: string;
  reason: string;
  recommendation: string;
  cta: string;
  target: SectionId;
  impactValue: number;
  impactLabel: string;
  timeToStart: string;
  done: boolean;
  tone: MetricTone;
  icon: LucideIcon;
};

function buildDailyDecisionActions(
  unresolvedIssues: number,
  stalledProducts: number,
  activeDebts: number,
  selectedPeriod: (typeof periodData)[keyof typeof periodData],
): DailyDecisionAction[] {
  const issueImpact = unresolvedIssues * 320;
  const inventoryImpact = stalledProducts * 75;
  const debtImpact = activeDebts * 190;
  const marginGap = Math.max(0, Math.round((22 - selectedPeriod.margin) * Math.max(selectedPeriod.sales, 1) * 0.01));

  const actions: DailyDecisionAction[] = [
    {
      title: unresolvedIssues > 0 ? "Fechar pendências antes do relatório" : "Fecho mensal sem pendências críticas",
      shortTitle: unresolvedIssues > 0 ? "Fechar pendências" : "Fecho controlado",
      reason: unresolvedIssues > 0 ? `${unresolvedIssues} movimentos ainda precisam de validação` : "sem bloqueio crítico de conciliação",
      recommendation:
        unresolvedIssues > 0
          ? `Resolver ${unresolvedIssues} pendências primeiro evita retrabalho e melhora a confiança do relatório executivo.`
          : "Manter validação final e guardar snapshot para comparação histórica.",
      cta: unresolvedIssues > 0 ? "Resolver conciliação" : "Ver conciliação",
      target: "conciliacao",
      impactValue: issueImpact,
      impactLabel: "risco de fecho",
      timeToStart: unresolvedIssues > 0 ? "12 min" : "2 min",
      done: unresolvedIssues === 0,
      tone: unresolvedIssues > 0 ? "danger" : "success",
      icon: ClipboardCheck,
    },
    {
      title: stalledProducts > 0 ? "Libertar capital parado em inventário" : "Inventário sem alerta de rotação crítica",
      shortTitle: stalledProducts > 0 ? "Libertar stock" : "Stock saudável",
      reason: stalledProducts > 0 ? `${stalledProducts} produtos estão parados há mais de 90 dias` : "sem produtos parados críticos",
      recommendation:
        stalledProducts > 0
          ? "Separar SKUs sem rotação para rever preço, exposição em marketplace ou plano de liquidação."
          : "Continuar a acompanhar margem e ruptura antes da próxima compra.",
      cta: stalledProducts > 0 ? "Rever inventário" : "Ver inventário",
      target: "inventario",
      impactValue: inventoryImpact,
      impactLabel: "capital parado",
      timeToStart: stalledProducts > 0 ? "18 min" : "3 min",
      done: stalledProducts === 0,
      tone: stalledProducts > 0 ? "warning" : "success",
      icon: PackageSearch,
    },
    {
      title: activeDebts > 0 ? "Cobrar e regularizar saldos abertos" : "Contas correntes sob controlo",
      shortTitle: activeDebts > 0 ? "Cobrar saldos" : "Saldos controlados",
      reason: activeDebts > 0 ? `${activeDebts} contas continuam abertas` : "sem saldos ativos críticos",
      recommendation:
        activeDebts > 0
          ? "Ordenar saldos por antiguidade e tratar primeiro valores vencidos ou sem confirmação documental."
          : "Manter aging atualizado e confirmar novos pagamentos antes do fecho.",
      cta: activeDebts > 0 ? "Priorizar cobrança" : "Ver financeiro",
      target: "financeiro",
      impactValue: debtImpact,
      impactLabel: "saldos em risco",
      timeToStart: activeDebts > 0 ? "9 min" : "2 min",
      done: activeDebts === 0,
      tone: activeDebts > 0 ? "navy" : "success",
      icon: WalletCards,
    },
    {
      title: marginGap > 0 ? "Investigar perda de margem no período" : "Margem operacional acima do alvo",
      shortTitle: marginGap > 0 ? "Rever margem" : "Margem saudável",
      reason: marginGap > 0 ? `margem atual de ${selectedPeriod.margin}% abaixo do alvo de 22%` : `${selectedPeriod.margin}% de margem no período`,
      recommendation:
        marginGap > 0
          ? "Comparar canais, custos e comissões para encontrar onde a venda parece boa mas destrói lucro."
          : "Guardar snapshot e comparar a margem com o próximo período.",
      cta: marginGap > 0 ? "Analisar canais" : "Guardar histórico",
      target: marginGap > 0 ? "financeiro" : "nuvem",
      impactValue: marginGap,
      impactLabel: "margem recuperável",
      timeToStart: marginGap > 0 ? "15 min" : "2 min",
      done: marginGap === 0,
      tone: marginGap > 0 ? "warning" : "success",
      icon: BarChart3,
    },
  ];

  return actions.sort((a, b) => Number(a.done) - Number(b.done) || b.impactValue - a.impactValue);
}

function ProductShowcaseLanding({ onLogin, onRegister }: { onLogin: () => void; onRegister: () => void }) {
  const navItems = ["Produto", "Funcionalidades", "Módulos", "Integrações", "Casos de uso", "Preços", "Contacto"];
  const slugId = (value: string) =>
    value
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");

  const featurePages = [
    {
      id: "funcionalidades",
      eyebrow: "Funcionalidades",
      title: "Tudo o que a operação precisa para decidir melhor.",
      text:
        "O SEO lê ficheiros e documentos, transforma dados desorganizados em informação estruturada e apresenta recomendações com impacto financeiro. A empresa passa a acompanhar faturação, stock, pagamentos e anomalias no mesmo sistema.",
      items: [
        "Excel, CSV, PDF, SAF-T e fotografias com OCR local.",
        "Correção de dados desconfigurados e cálculos automáticos.",
        "Anomalias priorizadas por severidade e impacto financeiro.",
        "Pagamentos, inventário e documentos com histórico auditável.",
        "Excel organizado e relatórios PDF prontos para descarregar.",
      ],
      visual: "decision",
    },
    {
      id: "modulos",
      eyebrow: "Módulos",
      title: "Uma plataforma modular, começando pelo que gera valor imediato.",
      text:
        "Cada módulo resolve uma dor operacional concreta. O sistema começa como apoio à análise, mas a arquitetura já prepara evolução para ERP com inventário, financeiro, conciliação, IA e integrações.",
      items: [
        "Centro de Decisão: recomenda as 3 ações com maior impacto.",
        "Financeiro: receitas, despesas, margens, aging e contas correntes.",
        "Inventário: stock atual, rotação, capital parado e ruptura.",
        "Anomalias: duplicados, inconsistências, divergências e exceções.",
        "IA Analista: conversa contextual, ficheiros e resultados exportáveis.",
      ],
      visual: "modules",
    },
    {
      id: "integracoes",
      eyebrow: "Integrações",
      title: "Preparado para ligar marketplaces, loja online e contabilidade.",
      text:
        "A primeira versão trabalha com ficheiros exportados. A evolução natural é conectar fontes reais para reduzir trabalho manual e criar uma visão única das vendas, custos e documentos.",
      items: [
        "Excel e CSV para arranque imediato sem mudar processos.",
        "Ovoko e Recambio para desempenho por marketplace.",
        "WooCommerce e Shopify para loja online.",
        "Moloni e Primavera para documentos e contabilidade.",
        "API segura para multiempresa, auditoria e automações.",
      ],
      visual: "integrations",
    },
    {
      id: "casos-de-uso",
      eyebrow: "Casos de uso",
      title: "Aplicações reais para uma empresa de peças automóveis.",
      text:
        "O SEO foi desenhado para rotinas concretas: fecho mensal, análise de marketplaces, clientes em atraso, fornecedores por pagar, inventário parado e preparação de relatórios para gestão.",
      items: [
        "Fecho mensal com pendências identificadas antes do relatório.",
        "Comparação entre loja física, loja online, Ovoko e Recambio.",
        "Lista de clientes e fornecedores por antiguidade de saldo.",
        "Produtos parados há mais de 90 dias com capital estimado.",
        "Relatório antes/depois para demonstrar ganhos no estágio.",
      ],
      visual: "usecases",
    },
  ] as const;

  return (
    <main className="min-h-screen bg-[#f5f5f7] text-[#1d1d1f]">
      <header className="sticky top-0 z-30 border-b border-black/5 bg-[#f5f5f7]/85 backdrop-blur-xl">
        <div className="mx-auto flex h-12 max-w-7xl items-center justify-between px-5">
          <button className="flex items-center gap-2 text-left" onClick={onLogin} type="button" aria-label="SEO">
            <span className="text-lg font-semibold tracking-tight">SEO</span>
          </button>
          <nav className="hidden items-center gap-8 text-xs text-[#1d1d1f] md:flex">
            {navItems.map((item) => (
              <a key={item} className="hover:text-black/60" href={item === "Produto" ? "#produto" : "#" + slugId(item)}>
                {item}
              </a>
            ))}
          </nav>
          <button className="text-xs font-medium hover:text-black/60" onClick={onLogin} type="button">
            Entrar
          </button>
        </div>
      </header>

      <section id="produto" className="mx-auto flex min-h-[calc(100vh-48px)] max-w-7xl flex-col items-center overflow-hidden px-5 pt-16 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#0071e3]">SEO Intelligence</p>
        <h1 className="mt-4 max-w-5xl text-5xl font-semibold tracking-tight text-[#1d1d1f] md:text-7xl">
          Transforme Excel, stock e marketplaces em decisões automáticas.
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-[#6e6e73] md:text-2xl">
          Reduza tempo no fecho mensal, detete capital parado e analise margens por canal sem depender de mapas dispersos.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <button
            className="rounded-full bg-[#0071e3] px-7 py-3 text-base font-semibold text-white shadow-[0_12px_35px_rgba(0,113,227,0.22)] hover:bg-[#0077ed]"
            onClick={onRegister}
            type="button"
          >
            Experimentar grátis
          </button>
          <button
            className="rounded-full border border-black/15 bg-white px-7 py-3 text-base font-semibold text-[#1d1d1f] hover:border-black/25"
            onClick={onLogin}
            type="button"
          >
            Ver demonstração
          </button>
        </div>

        <div className="mt-9 grid w-full max-w-4xl gap-3 text-left sm:grid-cols-3">
          {[
            ["Fecho mensal", "Relatórios em minutos, não horas."],
            ["Capital parado", "Produtos críticos e sem rotação visíveis."],
            ["Margens reais", "Ovoko, Recambio e loja online comparados."],
          ].map(([title, detail]) => (
            <div key={title} className="rounded-2xl bg-white p-4 shadow-[0_14px_50px_rgba(0,0,0,0.06)]">
              <p className="text-sm font-semibold text-[#1d1d1f]">{title}</p>
              <p className="mt-1 text-sm leading-5 text-[#6e6e73]">{detail}</p>
            </div>
          ))}
        </div>

        <LandingProductPreview />
      </section>

      <section className="mx-auto max-w-7xl px-5 py-14 md:py-20">
        <div className="mb-8 max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#0071e3]">Do ficheiro à decisão</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight md:text-5xl">Um fluxo completo, sem alterar a rotina da equipa.</h2>
          <p className="mt-4 text-base leading-7 text-[#6e6e73]">O SEO recebe os dados atuais, corrige inconsistências e devolve informação pronta para validar, acompanhar e exportar.</p>
        </div>

        <div className="grid gap-3 lg:grid-cols-4">
          {[
            ["01", "Importe os dados", "Excel, CSV, PDF, SAF-T ou fotografia de uma fatura.", Upload, "bg-blue-50 text-blue-700"],
            ["02", "IA e OCR analisam", "Organizam documentos, cálculos, pagamentos e inventário.", BrainCircuit, "bg-violet-50 text-violet-700"],
            ["03", "Valide as exceções", "Anomalias são priorizadas por risco e impacto financeiro.", ShieldCheck, "bg-amber-50 text-amber-700"],
            ["04", "Exporte e acompanhe", "Descarregue Excel/PDF e mantenha o histórico na nuvem.", Download, "bg-emerald-50 text-emerald-700"],
          ].map(([step, title, detail, Icon, tone]) => {
            const StepIcon = Icon as LucideIcon;
            return (
              <article key={String(step)} className="group relative rounded-[24px] border border-black/[0.06] bg-white p-5 shadow-[0_14px_45px_rgba(0,0,0,0.045)] transition hover:-translate-y-1 hover:shadow-[0_20px_60px_rgba(0,0,0,0.08)] md:p-6">
                <div className="flex items-start gap-4 lg:block">
                  <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${String(tone)}`}>
                    <StepIcon size={21} aria-hidden="true" />
                  </span>
                  <div className="min-w-0 lg:mt-7">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold tracking-[0.16em] text-[#86868b]">{String(step)}</span>
                      <span className="h-px flex-1 bg-black/[0.07]" />
                    </div>
                    <h3 className="mt-2 text-lg font-semibold tracking-tight text-[#1d1d1f] md:text-xl">{String(title)}</h3>
                    <p className="mt-2 text-sm leading-6 text-[#6e6e73]">{String(detail)}</p>
                  </div>
                </div>
              </article>
            );
          })}
        </div>

        <div className="mt-6 flex flex-col gap-3 rounded-[24px] bg-[#1d1d1f] px-5 py-5 text-white sm:flex-row sm:items-center sm:justify-between md:px-7">
          <div>
            <p className="font-semibold">Pronto para analisar um ficheiro real?</p>
            <p className="mt-1 text-sm text-white/60">Os documentos permanecem associados à empresa e às permissões do utilizador.</p>
          </div>
          <button className="shrink-0 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-black hover:bg-blue-50" onClick={onLogin} type="button">
            Abrir demonstração
          </button>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-3 px-5 py-14 md:grid-cols-4" aria-label="Prova social">
        {[
          ["+18.500", "linhas processadas"],
          ["+12.000€", "capital libertado"],
          ["+120h", "poupadas em fechos"],
          ["3", "empresas piloto"],
        ].map(([value, label]) => (
          <article key={label} className="rounded-[24px] bg-white p-6 text-center shadow-[0_18px_60px_rgba(0,0,0,0.06)]">
            <p className="text-3xl font-semibold tracking-tight">{value}</p>
            <p className="mt-2 text-sm text-[#6e6e73]">{label}</p>
          </article>
        ))}
      </section>

      {featurePages.map((page, index) => (
        <section
          key={page.id}
          id={page.id}
          className="mx-auto grid min-h-[78vh] max-w-7xl items-center gap-10 px-5 py-16 lg:grid-cols-[0.92fr_1.08fr]"
        >
          <div className={index % 2 === 1 ? "lg:order-2" : ""}>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#0071e3]">{page.eyebrow}</p>
            <h2 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-[#1d1d1f] md:text-5xl">{page.title}</h2>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[#6e6e73]">{page.text}</p>
            <div className="mt-7 grid gap-3">
              {page.items.map((item) => (
                <div key={item} className="flex gap-3 rounded-2xl bg-white p-4 shadow-[0_14px_45px_rgba(0,0,0,0.05)]">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#0071e3] text-xs font-semibold text-white">
                    ✓
                  </span>
                  <p className="text-sm leading-6 text-[#1d1d1f]">{item}</p>
                </div>
              ))}
            </div>
          </div>
          <LandingSectionVisual variant={page.visual} />
        </section>
      ))}

      <section id="precos" className="mx-auto max-w-6xl px-5 py-12">
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#0071e3]">Preços</p>
          <h2 className="mt-2 text-4xl font-semibold tracking-tight">Planos para começar pequeno e escalar.</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-[#6e6e73]">
            A lógica comercial acompanha a estratégia de implementação gradual: começar com análise de ficheiros,
            provar valor e evoluir para integrações, multiempresa e relatórios premium.
          </p>
        </div>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ["Starter", "29€", "1 utilizador", "1 empresa", "Até 5.000 linhas/mês"],
            ["Pro", "79€", "3 utilizadores", "3 empresas", "Até 50.000 linhas/mês"],
            ["Business", "199€", "10 utilizadores", "multiempresa", "API e relatórios premium"],
          ].map(([plan, price, users, companies, limit], index) => (
            <article key={plan} className={"rounded-[28px] p-7 shadow-[0_18px_60px_rgba(0,0,0,0.07)] " + (index === 1 ? "bg-[#1d1d1f] text-white" : "bg-white")}>
              <p className="text-lg font-semibold">{plan}</p>
              <p className="mt-4 text-4xl font-semibold tracking-tight">{price}<span className="text-base font-medium opacity-60">/mês</span></p>
              <div className="mt-6 space-y-3 text-sm opacity-80">
                <p>{users}</p>
                <p>{companies}</p>
                <p>{limit}</p>
              </div>
              <button className={"mt-7 w-full rounded-full px-5 py-3 text-sm font-semibold " + (index === 1 ? "bg-white text-[#1d1d1f]" : "bg-[#0071e3] text-white")} onClick={onRegister} type="button">
                Começar
              </button>
            </article>
          ))}
        </div>
      </section>

      <section id="conformidade" className="mx-auto grid max-w-7xl items-center gap-10 px-5 py-16 lg:grid-cols-[1fr_0.9fr]">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#0071e3]">Conformidade</p>
          <h2 className="mt-2 text-4xl font-semibold tracking-tight">RGPD, AI Act e supervisão humana.</h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-[#6e6e73]">
            O SEO atua como ferramenta de apoio à decisão. As análises são sugestões automáticas,
            com explicação e confiança, mas exigem validação por profissional responsável antes de qualquer reporte oficial.
          </p>
          <div className="mt-7 grid gap-3 sm:grid-cols-2">
            {[
              ["Auditoria", "Sugestões rastreáveis e sujeitas a validação humana."],
              ["RGPD", "Minimização, controlo de acesso, auditoria e proteção de dados."],
              ["AI Act", "Transparência, explicabilidade e supervisão humana."],
              ["União Europeia", "Respeito por direitos fundamentais, segurança e responsabilidade."],
            ].map(([title, detail]) => (
              <div key={title} className="rounded-2xl bg-white p-5 shadow-[0_14px_45px_rgba(0,0,0,0.05)]">
                <p className="text-sm font-semibold">{title}</p>
                <p className="mt-2 text-sm leading-5 text-[#6e6e73]">{detail}</p>
              </div>
            ))}
          </div>
        </div>
        <LandingSectionVisual variant="security" />
      </section>

      <section id="contacto" className="mx-auto max-w-6xl px-5 pb-14">
        <article className="rounded-[32px] bg-[#1d1d1f] p-8 text-center text-white shadow-[0_24px_80px_rgba(0,0,0,0.18)]">
          <h2 className="text-3xl font-semibold tracking-tight">Quer ver o SEO com os dados da sua empresa?</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-white/65">
            A melhor demonstração começa com um ficheiro real: vendas, stock, contas correntes ou marketplace. Em minutos,
            o SEO mostra prioridades, impacto financeiro e relatório executivo.
          </p>
          <button className="mt-5 rounded-full bg-[#0071e3] px-6 py-3 text-sm font-semibold text-white hover:bg-[#0077ed]" onClick={onLogin} type="button">
            Ver demonstração
          </button>
        </article>
      </section>
    </main>
  );
}

function LandingProductPreview() {
  return (
    <div className="relative mt-14 w-full max-w-5xl">
      <div className="absolute inset-x-10 bottom-0 h-24 rounded-full bg-black/10 blur-3xl" />
      <div className="relative overflow-hidden rounded-t-[36px] border border-black/10 bg-[#101828] text-left shadow-[0_32px_90px_rgba(0,0,0,0.22)]">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.06] px-5 py-4">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-[#ff5f57]" />
            <span className="h-3 w-3 rounded-full bg-[#ffbd2e]" />
            <span className="h-3 w-3 rounded-full bg-[#28c840]" />
          </div>
          <span className="text-xs font-medium text-white/45">demonstração visual</span>
        </div>

        <div className="grid gap-0 md:grid-cols-[220px_1fr]">
          <aside className="hidden border-r border-white/10 bg-white/[0.04] p-5 md:block">
            <p className="text-sm font-semibold text-white">SEO</p>
            <div className="mt-6 space-y-2 text-xs text-white/55">
              {["Dashboard", "Financeiro", "Inventário", "IA Analista"].map((item, index) => (
                <div key={item} className={`rounded-xl px-3 py-2 ${index === 0 ? "bg-white text-[#101828]" : "bg-white/[0.05]"}`}>
                  {item}
                </div>
              ))}
            </div>
          </aside>

          <div className="p-5">
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-blue-200">Preview do produto</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Dashboard gerado após Excel</h2>
              </div>
              <span className="self-start rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white/70 md:self-auto">
                Dados fictícios
              </span>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-4">
              {[
                ["Vendas", "42.350€"],
                ["Lucro", "8.920€"],
                ["Margem", "21,1%"],
                ["Alertas", "7"],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl bg-white/[0.08] p-4">
                  <p className="text-xs text-white/50">{label}</p>
                  <p className="mt-2 text-xl font-semibold text-white">{value}</p>
                </div>
              ))}
            </div>

            <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_0.8fr]">
              <div className="rounded-2xl bg-white/[0.08] p-4">
                <div className="flex h-40 items-end gap-2">
                  {[46, 58, 52, 70, 64, 82, 74, 88].map((height, index) => (
                    <span key={index} className="flex-1 rounded-t-lg bg-gradient-to-t from-[#0071e3] to-[#7cc4ff]" style={{ height: `${height}%` }} />
                  ))}
                </div>
              </div>
              <div className="rounded-2xl bg-white/[0.08] p-4">
                <p className="text-sm font-semibold text-white">IA Analista</p>
                <p className="mt-3 text-sm leading-6 text-white/65">
                  Identifica prioridades e recomenda ações antes do fecho mensal.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LandingSectionVisual({ variant }: { variant: "decision" | "modules" | "integrations" | "usecases" | "security" }) {
  const content = {
    decision: {
      title: "Centro de Decisão",
      subtitle: "Prioridade financeira em tempo real",
      rows: [
        ["Fecho mensal", "Crítico", "3.250€"],
        ["Capital parado", "Atenção", "1.850€"],
        ["Saldos abertos", "Atenção", "2.276€"],
      ],
      stat: "82",
      statLabel: "Índice SEO",
    },
    modules: {
      title: "Módulos SEO",
      subtitle: "Fluxo operacional completo",
      rows: [
        ["Financeiro", "Margem e resultado", "ativo"],
        ["Inventário", "Stock e rotação", "ativo"],
        ["IA Analista", "Plano de ação", "ativo"],
      ],
      stat: "6",
      statLabel: "módulos",
    },
    integrations: {
      title: "Integrações",
      subtitle: "Fontes ligadas ao mesmo painel",
      rows: [
        ["Ovoko", "Marketplace", "planeado"],
        ["Recambio", "Marketplace", "planeado"],
        ["Moloni", "Contabilidade", "planeado"],
      ],
      stat: "API",
      statLabel: "futura",
    },
    usecases: {
      title: "Casos de uso",
      subtitle: "Rotinas que ganham velocidade",
      rows: [
        ["Fecho mensal", "2h → 10min", "ganho"],
        ["Cobrança", "aging automático", "controlo"],
        ["Stock", "+90 dias parado", "alerta"],
      ],
      stat: "120h",
      statLabel: "poupadas",
    },
    security: {
      title: "Confiança",
      subtitle: "Auditoria, permissões e validação humana",
      rows: [
        ["RGPD", "dados minimizados", "controlo"],
        ["Auditoria", "sugestão explicada", "humano"],
        ["Auditoria", "quem fez o quê", "rastro"],
      ],
      stat: "2FA",
      statLabel: "segurança",
    },
  }[variant];

  return (
    <div className="rounded-[34px] bg-[#101828] p-4 text-white shadow-[0_28px_90px_rgba(0,0,0,0.22)]">
      <div className="rounded-[26px] border border-white/10 bg-white/[0.04] p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-200">{content.subtitle}</p>
            <h3 className="mt-2 text-2xl font-semibold">{content.title}</h3>
          </div>
          <div className="rounded-2xl bg-white p-4 text-[#101828]">
            <p className="text-3xl font-semibold tracking-tight">{content.stat}</p>
            <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-[#6e6e73]">{content.statLabel}</p>
          </div>
        </div>

        <div className="mt-7 grid gap-3">
          {content.rows.map(([name, status, value]) => (
            <div key={name} className="grid grid-cols-[1fr_auto] gap-4 rounded-2xl bg-white/[0.08] p-4">
              <div>
                <p className="text-sm font-semibold">{name}</p>
                <p className="mt-1 text-xs text-white/55">{status}</p>
              </div>
              <span className="self-center rounded-full bg-[#0071e3] px-3 py-1 text-xs font-semibold text-white">{value}</span>
            </div>
          ))}
        </div>

        <div className="mt-7 h-32 rounded-2xl bg-white/[0.08] p-4">
          <div className="flex h-full items-end gap-2">
            {[38, 58, 46, 76, 64, 88, 72].map((height, index) => (
              <span
                key={index}
                className="flex-1 rounded-t-lg bg-gradient-to-t from-[#0071e3] to-[#8fd0ff]"
                style={{ height: `${height}%` }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function MinimalLoginPage({
  error,
  onSubmit,
  onBack,
  onRegister,
}: {
  error: string;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onBack: () => void;
  onRegister: () => void;
}) {
  return (
    <main className="min-h-screen bg-[linear-gradient(145deg,#050b14,#071426_52%,#050b14)] text-white">
      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-8">
        <button className="mb-10 self-center" onClick={onBack} type="button">
          <SeoWordmark variant="dark" size="header" />
        </button>

        <section className="rounded-[28px] border border-white/10 bg-white/[0.07] p-7 shadow-[0_32px_90px_rgba(0,0,0,0.35)] backdrop-blur">
          <div className="text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-200">Área reservada</p>
            <h1 className="mt-3 text-3xl font-semibold text-white">Entrar</h1>
            <p className="mt-3 text-sm leading-6 text-blue-100">Aceda como administrador ou entre com uma conta de cliente registada.</p>
          </div>

          <form className="mt-8" onSubmit={onSubmit}>
            <label className="block text-sm font-semibold text-blue-100" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              name="email"
              className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/10 px-4 text-white placeholder:text-blue-200"
              placeholder="admin@seo.local"
              type="email"
              required
            />

            <label className="mt-5 block text-sm font-semibold text-blue-100" htmlFor="password">
              Palavra-passe
            </label>
            <input
              id="password"
              name="password"
              className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/10 px-4 text-white placeholder:text-blue-200"
              placeholder="********"
              type="password"
              required
            />

            {error && <p className="mt-4 rounded-xl border border-red-300/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p>}

            <button
              className="mt-7 w-full rounded-xl bg-white px-5 py-3 text-sm font-semibold text-navy-950 shadow-soft hover:bg-blue-50"
              type="submit"
            >
              Continuar
            </button>
          </form>

          <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.06] p-4 text-sm leading-6 text-blue-100">
            <p className="font-semibold text-white">Acesso protegido</p>
            <p className="mt-1">
              As credenciais e permissões são validadas pelo backend. Nenhuma palavra-passe é guardada no navegador.
            </p>
          </div>

          <button className="mt-5 w-full rounded-xl border border-white/15 px-5 py-3 text-sm font-semibold text-white hover:bg-white/10" onClick={onRegister} type="button">
            Registrar conta de cliente
          </button>
        </section>

        <button className="mt-6 text-sm font-semibold text-blue-100 hover:text-white" onClick={onBack} type="button">
          Voltar
        </button>
      </div>
    </main>
  );
}

function RegisterPage({
  error,
  onSubmit,
  onBack,
  onLogin,
}: {
  error: string;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onBack: () => void;
  onLogin: () => void;
}) {
  return (
    <main className="min-h-screen bg-[linear-gradient(145deg,#050b14,#071426_52%,#050b14)] text-white">
      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-8">
        <button className="mb-10 self-center" onClick={onBack} type="button">
          <SeoWordmark variant="dark" size="header" />
        </button>

        <section className="rounded-[28px] border border-white/10 bg-white/[0.07] p-7 shadow-[0_32px_90px_rgba(0,0,0,0.35)] backdrop-blur">
          <div className="text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-200">Nova conta</p>
            <h1 className="mt-3 text-3xl font-semibold text-white">Registrar cliente</h1>
            <p className="mt-3 text-sm leading-6 text-blue-100">
              Crie uma conta de cliente para carregar ficheiros, consultar relatórios e acompanhar recomendações.
            </p>
          </div>

          <form className="mt-8" onSubmit={onSubmit}>
            <label className="block text-sm font-semibold text-blue-100" htmlFor="register-name">
              Nome
            </label>
            <input
              id="register-name"
              name="name"
              className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/10 px-4 text-white placeholder:text-blue-200"
              placeholder="Nome do cliente"
              required
            />

            <label className="mt-5 block text-sm font-semibold text-blue-100" htmlFor="register-email">
              Email
            </label>
            <input
              id="register-email"
              name="email"
              className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/10 px-4 text-white placeholder:text-blue-200"
              placeholder="cliente@empresa.pt"
              type="email"
              required
            />

            <label className="mt-5 block text-sm font-semibold text-blue-100" htmlFor="register-password">
              Palavra-passe
            </label>
            <input
              id="register-password"
              name="password"
              className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/10 px-4 text-white placeholder:text-blue-200"
              minLength={8}
              placeholder="mínimo 8 caracteres"
              type="password"
              required
            />

            {error && <p className="mt-4 rounded-xl border border-red-300/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p>}

            <button
              className="mt-7 w-full rounded-xl bg-white px-5 py-3 text-sm font-semibold text-navy-950 shadow-soft hover:bg-blue-50"
              type="submit"
            >
              Criar conta e validar
            </button>
          </form>

          <button className="mt-5 w-full rounded-xl border border-white/15 px-5 py-3 text-sm font-semibold text-white hover:bg-white/10" onClick={onLogin} type="button">
            Já tenho conta
          </button>
        </section>

        <button className="mt-6 text-sm font-semibold text-blue-100 hover:text-white" onClick={onBack} type="button">
          Voltar
        </button>
      </div>
    </main>
  );
}

function MfaPage({
  error,
  challenge,
  onSubmit,
  onBack,
}: {
  error: string;
  challenge: SecurityChallenge | null;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onBack: () => void;
}) {
  return (
    <main className="min-h-screen bg-[linear-gradient(145deg,#050b14,#071426_52%,#050b14)] text-white">
      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-8">
        <button className="mb-10 self-center" onClick={onBack} type="button">
          <SeoWordmark variant="dark" size="header" />
        </button>

        <section className="rounded-[28px] border border-white/10 bg-white/[0.07] p-7 shadow-[0_32px_90px_rgba(0,0,0,0.35)] backdrop-blur">
          <div className="text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-200">Verificação segura</p>
            <h1 className="mt-3 text-3xl font-semibold text-white">Código de acesso</h1>
            <p className="mt-3 text-sm leading-6 text-blue-100">
              Segunda autenticação obrigatória antes de carregar ou consultar dados sensíveis.
            </p>
          </div>

          <form className="mt-8" onSubmit={onSubmit}>
            <label className="block text-sm font-semibold text-blue-100" htmlFor="securityCode">
              Código temporário
            </label>
            <input
              id="securityCode"
              name="securityCode"
              className="mt-2 h-12 w-full rounded-xl border border-white/10 bg-white/10 px-4 text-center text-lg font-semibold tracking-[0.32em] text-white placeholder:text-blue-200"
              inputMode="numeric"
              maxLength={6}
              placeholder="000000"
              required
            />

            {error && <p className="mt-3 rounded-xl border border-red-300/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</p>}

            <button
              className="mt-7 w-full rounded-xl bg-white px-5 py-3 text-sm font-semibold text-navy-950 shadow-soft hover:bg-blue-50"
              type="submit"
            >
              Validar e continuar
            </button>
          </form>

          <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.06] p-4 text-sm leading-6 text-blue-100">
            {challenge?.deliveryHint ?? "Código temporário criado. Confirme a autenticação para continuar."}
            {challenge?.developmentCode && (
              <span className="mt-2 block font-semibold text-white">
                Código de desenvolvimento: {challenge.developmentCode}
              </span>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

function StartScreen({
  fileInputRef,
  onUpload,
  onDownloadTemplate,
  onBackHome,
}: {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onUpload: (file: File | undefined) => void;
  onDownloadTemplate: () => void;
  onBackHome: () => void;
}) {
  return (
    <main className="min-h-screen bg-[#f5f5f7] text-[#1d1d1f]">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-5 py-8">
        <header className="flex items-center justify-between">
          <button className="flex items-center gap-3 text-left" onClick={onBackHome} type="button">
            <SeoWordmark variant="light" size="header" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-200">Sistema</p>
              <h1 className="text-base font-semibold">Eficiência Operacional</h1>
            </div>
          </button>
          <span className="hidden rounded-full border border-black/10 bg-white px-4 py-2 text-sm font-medium text-[#6e6e73] shadow-[0_8px_30px_rgba(0,0,0,0.04)] sm:inline-flex">
            MVP inteligente
          </span>
        </header>

        <section className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[1fr_0.86fr]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-[#0071e3] shadow-[0_8px_30px_rgba(0,0,0,0.04)]">
              <Sparkles size={16} aria-hidden="true" />
              Comece em menos de 2 minutos
            </div>
            <h2 className="mt-6 max-w-3xl text-4xl font-semibold leading-tight tracking-[-0.02em] text-[#1d1d1f] md:text-6xl">
              Carregue um ficheiro e veja o Centro de Decisão nascer.
            </h2>
            <p className="mt-5 max-w-2xl text-base leading-7 text-[#6e6e73] md:text-lg">
              Carregue o Excel ou PDF das faturas. Também pode usar CSV ou XML/SAF-T. A IA lê, valida e organiza os documentos,
              calcula impacto financeiro e mostra que decisão deve ser tomada primeiro.
            </p>

            <div className="mt-8 grid gap-3 md:grid-cols-3">
              <ProcessStep number="1" title="Carregar faturas" detail="Excel ou PDF; também CSV e XML/SAF-T." />
              <ProcessStep number="2" title="Analisar" detail="IA classifica, valida e organiza." />
              <ProcessStep number="3" title="Agir" detail="Centro de Decisão e PDF executivo." />
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                className="rounded-full bg-[#0071e3] px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_35px_rgba(0,113,227,0.22)] hover:bg-[#0077ed]"
                onClick={() => fileInputRef.current?.click()}
                type="button"
              >
                Carregar ficheiro agora
              </button>
              <button
                className="rounded-full border border-black/10 bg-white px-5 py-3 text-sm font-semibold text-[#1d1d1f] hover:border-black/20"
                onClick={onDownloadTemplate}
                type="button"
              >
                Baixar modelo CSV
              </button>
            </div>
          </div>

          <div className="rounded-[32px] bg-white p-5 shadow-[0_24px_80px_rgba(0,0,0,0.08)]">
            <input
              ref={fileInputRef}
              className="hidden"
              type="file"
              accept=".xlsx,.pdf,.csv,.txt,.xml,.jpg,.jpeg,.png"
              onChange={(event) => {
                onUpload(event.target.files?.[0]);
                event.currentTarget.value = "";
              }}
            />
            <button
              className="flex min-h-[280px] w-full flex-col items-center justify-center rounded-[24px] border border-dashed border-black/15 bg-[#f5f5f7] px-6 py-10 text-center transition hover:border-[#0071e3] hover:bg-white"
              onClick={() => fileInputRef.current?.click()}
              type="button"
            >
              <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[#1d1d1f] text-white shadow-soft">
                <Upload size={28} aria-hidden="true" />
              </span>
              <span className="mt-6 text-xl font-semibold text-[#1d1d1f]">Selecionar Excel ou PDF das faturas</span>
              <span className="mt-2 max-w-sm text-sm leading-6 text-[#6e6e73]">
                Aceita `.xlsx`, `.pdf`, `.jpg` e `.png`, além de `.csv`, `.txt` e `.xml` (SAF-T). Fotografias e PDFs
                digitalizados são reconhecidos pelo OCR local, sem enviar o documento para serviços externos.
              </span>
            </button>

            <div className="mt-4">
              <button
                className="w-full rounded-full bg-[#0071e3] px-4 py-3 text-sm font-semibold text-white hover:bg-[#0077ed]"
                onClick={() => fileInputRef.current?.click()}
                type="button"
              >
                Carregar ficheiro
              </button>
            </div>

            <div className="mt-5 grid gap-3">
              {[
                ["Sem compromisso", "Funciona em paralelo aos processos atuais."],
                ["Dados reais", "O dashboard só é gerado depois da importação."],
                ["Validação humana", "Decisões oficiais continuam sob responsabilidade humana."],
              ].map(([title, detail]) => (
                <div key={title} className="rounded-xl border border-black/10 bg-[#f5f5f7] p-4 text-sm">
                  <p className="font-semibold text-[#1d1d1f]">{title}</p>
                  <p className="mt-1 leading-5 text-[#6e6e73]">{detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function ProcessStep({ number, title, detail }: { number: string; title: string; detail: string }) {
  return (
    <div className="rounded-[24px] bg-white p-4 shadow-[0_14px_45px_rgba(0,0,0,0.06)]">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#1d1d1f] text-sm font-semibold text-white">
        {number}
      </div>
      <p className="mt-4 text-sm font-semibold text-[#1d1d1f]">{title}</p>
      <p className="mt-1 text-sm leading-5 text-[#6e6e73]">{detail}</p>
    </div>
  );
}

function ReconciliationView({
  fileInputRef,
  issues,
  onImport,
  onResolveAll,
  onResolveIssue,
}: {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  issues: ReconciliationIssue[];
  onImport: (file: File | undefined) => void;
  onResolveAll: () => void;
  onResolveIssue: (issueId: number) => void;
}) {
  const [statusFilter, setStatusFilter] = useState<"Abertas" | "Críticas" | "Resolvidas" | "Todas">("Abertas");
  const [categoryFilter, setCategoryFilter] = useState("Todas");
  const [anomalySearch, setAnomalySearch] = useState("");
  const parseIssueValue = (value: string) => {
    const normalized = value.replace(/[^\d,.-]/g, "").replace(/\.(?=\d{3}(?:\D|$))/g, "").replace(",", ".");
    return Math.abs(Number.parseFloat(normalized) || 0);
  };
  const describeIssue = (issue: ReconciliationIssue) => {
    const text = `${issue.issue} ${issue.document}`.toLocaleLowerCase("pt-PT");
    const amount = parseIssueValue(issue.value);
    const category = text.includes("invent") || text.includes("stock")
      ? "Inventário"
      : text.includes("pagamento") || text.includes("vencid")
        ? "Pagamentos"
        : text.includes("duplic")
          ? "Duplicados"
          : text.includes("data") || text.includes("total") || text.includes("iva")
            ? "Documentos"
            : "Classificação";
    const severity = issue.status === "Resolvido"
      ? "Resolvida"
      : issue.status === "Alerta" || amount >= 2500 || text.includes("negativo") || text.includes("duplic")
        ? "Crítica"
        : amount >= 500 || text.includes("baixa confiança") || text.includes("divergência")
          ? "Média"
          : "Baixa";
    const recommendation = category === "Inventário"
      ? "Confirmar contagem física e o último movimento antes de ajustar o stock."
      : category === "Pagamentos"
        ? "Validar a fatura, contactar a entidade e registar a decisão."
        : category === "Duplicados"
          ? "Comparar número, entidade e valor; manter apenas o documento válido."
          : category === "Documentos"
            ? "Conferir os dados originais e recalcular os totais antes da exportação."
            : "Confirmar a natureza do movimento e atribuir a classificação correta.";
    return { amount, category, severity, recommendation };
  };
  const enriched = issues.map((issue) => ({ issue, ...describeIssue(issue) }));
  const unresolved = enriched.filter((item) => item.issue.status !== "Resolvido");
  const critical = unresolved.filter((item) => item.severity === "Crítica");
  const amountAtRisk = unresolved.reduce((sum, item) => sum + item.amount, 0);
  const categories = ["Todas", ...Array.from(new Set(enriched.map((item) => item.category)))];
  const filtered = enriched
    .filter((item) => {
      if (statusFilter === "Abertas" && item.issue.status === "Resolvido") return false;
      if (statusFilter === "Críticas" && item.severity !== "Crítica") return false;
      if (statusFilter === "Resolvidas" && item.issue.status !== "Resolvido") return false;
      if (categoryFilter !== "Todas" && item.category !== categoryFilter) return false;
      const query = anomalySearch.trim().toLocaleLowerCase("pt-PT");
      return !query || `${item.issue.document} ${item.issue.source} ${item.issue.issue}`.toLocaleLowerCase("pt-PT").includes(query);
    })
    .sort((a, b) => {
      const order: Record<string, number> = { Crítica: 0, Média: 1, Baixa: 2, Resolvida: 3 };
      return order[a.severity] - order[b.severity] || b.amount - a.amount;
    });

  return (
    <section className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={AlertTriangle} label="Anomalias abertas" value={String(unresolved.length)} delta={`${critical.length} críticas`} tone="danger" />
        <MetricCard icon={Euro} label="Valor em análise" value={formatCurrency(amountAtRisk)} delta="impacto financeiro associado" tone="warning" />
        <MetricCard icon={CheckCircle2} label="Resolvidas" value={String(issues.length - unresolved.length)} delta="com registo de auditoria" tone="success" />
        <MetricCard icon={ShieldCheck} label="Taxa de controlo" value={`${issues.length ? Math.round(((issues.length - unresolved.length) / issues.length) * 100) : 100}%`} delta="anomalias tratadas" tone="navy" />
      </div>

      {critical.length > 0 && (
        <div className="flex flex-col gap-4 rounded-2xl border border-red-400/20 bg-red-500/10 p-5 text-red-50 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-red-300">Atenção prioritária</p>
            <p className="mt-2 font-semibold">{critical.length} anomalia(s) crítica(s) devem ser verificadas antes do próximo relatório.</p>
            <p className="mt-1 text-sm text-red-100/70">Comece pelas ocorrências de maior valor; a resolução fica registada na auditoria.</p>
          </div>
          <button className="rounded-xl bg-red-400 px-4 py-2.5 text-sm font-semibold text-red-950 hover:bg-red-300" onClick={() => setStatusFilter("Críticas")} type="button">
            Ver prioridades
          </button>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Importar anomalias" action="Selecionar ficheiro" onAction={() => fileInputRef.current?.click()}>
        <input
          ref={fileInputRef}
          className="hidden"
          type="file"
          accept=".csv,.txt"
          onChange={(event) => {
            onImport(event.target.files?.[0]);
            event.currentTarget.value = "";
          }}
        />
        <div className="mb-4 grid gap-3 md:grid-cols-3">
          <UploadBox icon={FileSpreadsheet} title="CSV/TXT" detail="Importa listas externas de exceções" />
          <UploadBox icon={Building2} title="Deteção integrada" detail="Cruza documentos, pagamentos e stock" />
          <UploadBox icon={CheckCircle2} title="Rastreabilidade" detail="Regista resolução e utilizador" />
        </div>
        <p className="rounded-lg bg-mist px-4 py-3 text-sm text-slate-700">
          Formato simples para teste: documento;origem;valor;problema. A primeira linha pode ser cabeçalho.
        </p>
        </Panel>

        <Panel title="Distribuição por risco" action="Resolver todas" onAction={onResolveAll}>
          <div className="grid gap-3 sm:grid-cols-3">
            <MiniStat label="Críticas" value={String(critical.length)} />
            <MiniStat label="Médias/baixas" value={String(unresolved.length - critical.length)} />
            <MiniStat label="Resolvidas" value={String(issues.length - unresolved.length)} />
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            A prioridade combina estado, descrição e valor associado. A resolução automática não altera documentos nem stock.
          </p>
        </Panel>
      </div>

      <Panel title="Centro de anomalias" action="Exportar CSV" onAction={() => downloadCsv("anomalias-seo.csv", [
          ["Severidade", "Categoria", "Documento", "Origem", "Valor", "Anomalia", "Recomendação", "Estado"],
          ...enriched.map((item) => [item.severity, item.category, item.issue.document, item.issue.source, item.issue.value, item.issue.issue, item.recommendation, item.issue.status]),
        ])}>
        <div className="mb-5 space-y-3">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 text-slate-400" size={18} />
            <input
              aria-label="Pesquisar anomalias"
              className="h-11 w-full rounded-xl border border-line bg-white pl-10 pr-4 text-sm text-ink outline-none focus:border-blue-500"
              onChange={(event) => setAnomalySearch(event.target.value)}
              placeholder="Pesquisar documento, entidade ou problema"
              value={anomalySearch}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {(["Abertas", "Críticas", "Resolvidas", "Todas"] as const).map((filter) => (
              <button key={filter} className={`rounded-full px-3 py-2 text-sm font-semibold ${statusFilter === filter ? "bg-[#1d1d1f] text-white" : "bg-mist text-slate-700"}`} onClick={() => setStatusFilter(filter)} type="button">{filter}</button>
            ))}
            <span className="mx-1 hidden h-9 w-px bg-line sm:block" />
            {categories.map((category) => (
              <button key={category} className={`rounded-full px-3 py-2 text-sm font-semibold ${categoryFilter === category ? "bg-blue-600 text-white" : "bg-blue-50 text-blue-800"}`} onClick={() => setCategoryFilter(category)} type="button">{category}</button>
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-line p-10 text-center">
            <CheckCircle2 className="mx-auto text-emerald-500" size={34} />
            <p className="mt-3 font-semibold text-ink">Nenhuma anomalia neste filtro</p>
            <p className="mt-1 text-sm text-slate-500">Altere os filtros ou importe um novo ficheiro para análise.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((item) => {
              const severityStyle = item.severity === "Crítica" ? "bg-red-100 text-red-700" : item.severity === "Média" ? "bg-amber-100 text-amber-800" : item.severity === "Resolvida" ? "bg-emerald-100 text-emerald-700" : "bg-blue-100 text-blue-700";
              return (
                <article key={item.issue.id} className="grid gap-4 rounded-2xl border border-line bg-white p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${severityStyle}`}>{item.severity}</span>
                      <span className="rounded-full bg-mist px-2.5 py-1 text-xs font-semibold text-slate-600">{item.category}</span>
                      <span className="text-xs text-slate-400">#{item.issue.id}</span>
                    </div>
                    <div className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                      <h4 className="font-semibold text-ink">{item.issue.document}</h4>
                      <span className="text-sm text-slate-500">{item.issue.source}</span>
                      <span className="font-semibold text-slate-800">{item.issue.value}</span>
                    </div>
                    <p className="mt-2 text-sm font-medium text-slate-800">{item.issue.issue}</p>
                    <p className="mt-1 text-sm leading-5 text-slate-500">{item.recommendation}</p>
                  </div>
                  {item.issue.status === "Resolvido" ? (
                    <span className="inline-flex items-center gap-2 text-sm font-semibold text-emerald-700"><CheckCircle2 size={17} /> Resolvida</span>
                  ) : (
                    <button className="rounded-xl bg-[#1d1d1f] px-4 py-2.5 text-sm font-semibold text-white hover:bg-black" onClick={() => onResolveIssue(item.issue.id)} type="button">
                      Marcar resolvida
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </Panel>
    </section>
  );
}

function FinanceView({
  debts,
  summary,
  movements,
  debtFilter,
  onFilterChange,
  onMarkPaid,
  onExport,
}: {
  debts: DebtItem[];
  summary: (typeof periodData)[keyof typeof periodData];
  movements: ClassifiedMovement[];
  debtFilter: "Todos" | DebtState;
  onFilterChange: (filter: "Todos" | DebtState) => void;
  onMarkPaid: (id: number) => void;
  onExport: () => void;
}) {
  const totalOpen = debts.reduce((sum, debt) => (debt.state === "Pago" ? sum : sum + debt.amount), 0);
  const agingBuckets = [
    ["0-30 dias", debts.filter((debt) => debt.dueDays <= 30).reduce((sum, debt) => sum + debt.amount, 0)],
    ["31-60 dias", debts.filter((debt) => debt.dueDays > 30 && debt.dueDays <= 60).reduce((sum, debt) => sum + debt.amount, 0)],
    ["61-90 dias", debts.filter((debt) => debt.dueDays > 60 && debt.dueDays <= 90).reduce((sum, debt) => sum + debt.amount, 0)],
    ["+90 dias", debts.filter((debt) => debt.dueDays > 90).reduce((sum, debt) => sum + debt.amount, 0)],
  ] as const;
  const expenses = movements
    .filter((movement) => ["22", "24", "31", "62", "63", "68"].includes(movement.accountCode))
    .reduce((sum, movement) => sum + Math.abs(movement.amount), 0);

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={WalletCards} label="Valor em aberto" value={formatCurrency(totalOpen)} delta="contas filtradas" tone="danger" />
        <MetricCard icon={BarChart3} label="Margem média" value={`${summary.margin}%`} delta="calculada do ficheiro" tone="success" />
        <MetricCard icon={ArrowUpRight} label="Receitas" value={formatCurrency(summary.sales)} delta="ficheiro analisado" tone="navy" />
        <MetricCard icon={ArrowDownRight} label="Despesas" value={formatCurrency(expenses)} delta="ficheiro analisado" tone="warning" />
      </section>

      <Panel title="Aging de cobrança" action="Exportar" onAction={onExport}>
        <div className="grid gap-3 md:grid-cols-4">
          {agingBuckets.map(([label, value]) => (
            <div key={label} className="rounded-xl border border-line bg-mist p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
              <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(value)}</p>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Contas correntes" action="Exportar" onAction={onExport}>
        <div className="mb-4 flex flex-wrap gap-2">
          {(["Todos", "Em atraso", "A vencer", "Pago"] as Array<"Todos" | DebtState>).map((filter) => (
            <button
              key={filter}
              className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                debtFilter === filter ? "border-navy-900 bg-navy-900 text-white" : "border-line bg-white text-navy-800"
              }`}
              onClick={() => onFilterChange(filter)}
              type="button"
            >
              {filter}
            </button>
          ))}
        </div>
        <ActionTable
          columns={["Fatura", "Entidade", "Tipo", "Emissão", "Vencimento", "Valor", "Prazo", "Estado", "Ação"]}
          rows={debts.map((row) => [
            row.invoice,
            row.entity,
            row.type,
            row.issueDate,
            row.dueDate,
            formatCurrency(row.amount),
            `${row.dueDays} dias`,
            row.state,
            row.state === "Pago" ? "Pago" : "Marcar pago",
          ])}
          onAction={(rowIndex) => onMarkPaid(debts[rowIndex].id)}
        />
      </Panel>
    </>
  );
}

function InventoryView({
  inventory,
  search,
  onSearchChange,
  onRegisterSale,
  onExport,
}: {
  inventory: InventoryItem[];
  search: string;
  onSearchChange: (search: string) => void;
  onRegisterSale: (ref: string) => void;
  onExport: () => void;
}) {
  const [unitFilter, setUnitFilter] = useState("Todos");
  const [stockTypeFilter, setStockTypeFilter] = useState("Todos");
  const [movementFilter, setMovementFilter] = useState("Todos");
  const visibleInventory = inventory.filter((item) =>
    (unitFilter === "Todos" || item.unit === unitFilter)
    && (stockTypeFilter === "Todos" || item.stockType === stockTypeFilter)
    && (movementFilter === "Todos" || item.movementType === movementFilter),
  );
  const heatmapItems = visibleInventory.slice(0, 24);
  const averageMargin = inventory.length
    ? Math.round(inventory.reduce((sum, item) => sum + item.margin, 0) / inventory.length)
    : 0;
  const divergences = inventory.filter((item) => item.differenceQuantity !== 0);
  const negativeStock = inventory.filter((item) => item.physicalQuantity < 0);
  const inventoryValue = inventory.reduce((sum, item) => sum + item.stockValue, 0);
  const stockSegments = [
    ["Coimbra · Novo", inventory.filter((item) => item.unit === "Coimbra" && item.stockType === "Novo")],
    ["Coimbra · Usado", inventory.filter((item) => item.unit === "Coimbra" && item.stockType === "Usado")],
    ["Picoto · Novo", inventory.filter((item) => item.unit === "Picoto" && item.stockType === "Novo")],
    ["Picoto · Usado", inventory.filter((item) => item.unit === "Picoto" && item.stockType === "Usado")],
  ] as const;
  const movementSegments = (["Compra", "Venda", "Sucata", "Existente"] as const).map((movement) => [movement, inventory.filter((item) => item.movementType === movement)] as const);

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Boxes} label="Referências" value={String(inventory.length)} delta={`${inventory.reduce((sum, item) => sum + item.physicalQuantity, 0)} unidades físicas`} tone="navy" />
        <MetricCard icon={AlertTriangle} label="Divergências" value={String(divergences.length)} delta={`${negativeStock.length} stock negativo`} tone="danger" />
        <MetricCard icon={Euro} label="Valor inventário" value={formatCurrency(inventoryValue)} delta="quantidade física × custo" tone="success" />
        <MetricCard icon={ArrowUpRight} label="Margem média SKU" value={`${averageMargin}%`} delta="novo, usado e unidades" tone="warning" />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Panel title="Stock por unidade e condição" action="Ver inventário">
          <div className="grid gap-3 sm:grid-cols-2">
            {stockSegments.map(([label, items]) => (
              <div key={label} className="rounded-xl border border-line bg-mist p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
                <p className="mt-2 text-2xl font-semibold text-ink">{items.reduce((sum, item) => sum + item.physicalQuantity, 0)}</p>
                <p className="mt-1 text-xs text-slate-500">{items.length} referências · {formatCurrency(items.reduce((sum, item) => sum + item.stockValue, 0))}</p>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Movimentos de stock" action="Ver movimentos">
          <div className="grid gap-3 sm:grid-cols-2">
            {movementSegments.map(([label, items]) => (
              <div key={label} className="rounded-xl border border-line bg-mist p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
                <p className="mt-2 text-2xl font-semibold text-ink">{items.reduce((sum, item) => sum + Math.abs(item.movementQuantity), 0)}</p>
                <p className="mt-1 text-xs text-slate-500">{items.length} movimentos/registos</p>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      <Panel title="Mapa de stock físico e divergências" action="Exportar análise" onAction={onExport}>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
          {heatmapItems.map((item) => {
            const tone = item.differenceQuantity !== 0 || item.physicalQuantity < 0 ? "bg-red-100 text-red-800 border-red-200" : item.lastSaleDays > 90 ? "bg-amber-100 text-amber-900 border-amber-200" : "bg-emerald-100 text-emerald-800 border-emerald-200";
            return (
              <div key={item.ref} className={"min-h-24 rounded-xl border p-3 " + tone} title={item.product}>
                <p className="truncate text-xs font-semibold">{item.ref}</p>
                <p className="mt-2 text-2xl font-semibold">{item.physicalQuantity}</p>
                <p className="mt-1 truncate text-xs">{item.unit} · {item.stockType}</p>
                <p className="mt-1 truncate text-xs">Δ {item.differenceQuantity}</p>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel title="Inventário inteligente" action="Exportar" onAction={onExport}>
        <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
          <div className="flex items-center gap-2 rounded-lg border border-line bg-white px-3 py-2">
            <Search size={17} className="text-slate-500" aria-hidden="true" />
            <input className="w-full border-0 bg-transparent text-sm outline-none" value={search} onChange={(event) => onSearchChange(event.target.value)} placeholder="Procurar referência ou produto" aria-label="Pesquisar inventário" />
          </div>
          <select className="rounded-lg border border-line bg-white px-3 py-2 text-sm" value={unitFilter} onChange={(event) => setUnitFilter(event.target.value)} aria-label="Filtrar unidade">
            <option>Todos</option><option>Coimbra</option><option>Picoto</option>
          </select>
          <select className="rounded-lg border border-line bg-white px-3 py-2 text-sm" value={stockTypeFilter} onChange={(event) => setStockTypeFilter(event.target.value)} aria-label="Filtrar condição">
            <option>Todos</option><option>Novo</option><option>Usado</option>
          </select>
          <select className="rounded-lg border border-line bg-white px-3 py-2 text-sm" value={movementFilter} onChange={(event) => setMovementFilter(event.target.value)} aria-label="Filtrar movimento">
            <option>Todos</option><option>Compra</option><option>Venda</option><option>Sucata</option><option>Existente</option>
          </select>
        </div>
        <ActionTable
          columns={["Referência", "Produto", "Unidade", "Condição", "Movimento", "Qtd.", "Sistema", "Físico", "Diferença", "Valor", "Estado", "Ação"]}
          rows={visibleInventory.map((row) => [
            row.ref,
            row.product,
            row.unit,
            row.stockType,
            row.movementType,
            String(row.movementQuantity),
            String(row.systemQuantity),
            String(row.physicalQuantity),
            String(row.differenceQuantity),
            formatCurrency(row.stockValue),
            row.validationState,
            "Registar saída",
          ])}
          onAction={(rowIndex) => onRegisterSale(visibleInventory[rowIndex].ref)}
        />
      </Panel>
    </>
  );
}

function SncClassificationView({
  fileInputRef,
  movements,
  onImport,
  onReclassify,
  onExport,
}: {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  movements: ClassifiedMovement[];
  onImport: (file: File | undefined) => void;
  onReclassify: (movementId: number, accountCode: string) => void;
  onExport: () => void;
}) {
  const [selectedMovementId, setSelectedMovementId] = useState<number | null>(null);
  const [selectedAccountCode, setSelectedAccountCode] = useState(accountRules[0]?.code ?? "11");
  const selectedMovement = movements.find((movement) => movement.id === selectedMovementId) ?? null;
  const totalDebit = movements
    .filter((movement) => movement.movementType === "Débito")
    .reduce((sum, movement) => sum + Math.abs(movement.amount), 0);
  const totalCredit = movements
    .filter((movement) => movement.movementType === "Crédito")
    .reduce((sum, movement) => sum + Math.abs(movement.amount), 0);
  const averageConfidence = movements.length
    ? Math.round(movements.reduce((sum, movement) => sum + movement.confidence, 0) / movements.length)
    : 0;
  const highConfidence = movements.filter((movement) => movement.confidence >= 90).length;
  const mediumConfidence = movements.filter((movement) => movement.confidence >= 70 && movement.confidence < 90).length;
  const lowConfidence = movements.filter((movement) => movement.confidence < 70).length;

  return (
    <>
      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="IA de classificação SNC" action="Importar ficheiro" onAction={() => fileInputRef.current?.click()}>
          <input
            ref={fileInputRef}
            className="hidden"
            type="file"
            accept=".csv,.txt"
            onChange={(event) => {
              onImport(event.target.files?.[0]);
              event.currentTarget.value = "";
            }}
          />
          <div className="space-y-4">
            <div className="rounded-lg border border-line bg-mist p-4">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white text-navy-800">
                  <BookOpenCheck size={20} aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-ink">Leitura de ficheiros e sugestão de contas</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">
                    O ficheiro deve ter colunas como data, descrição, entidade e valor. A IA atribui uma conta do
                    SNC português por regras analíticas e palavras-chave.
                  </p>
                </div>
              </div>
            </div>
            <div className="grid gap-3">
              <button
                className="flex min-h-24 items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white p-4 text-left hover:border-navy-700"
                onClick={() => fileInputRef.current?.click()}
                type="button"
              >
                <Upload size={20} className="text-navy-800" aria-hidden="true" />
                <span>
                  <span className="block text-sm font-semibold text-ink">Importar CSV/TXT</span>
                  <span className="mt-1 block text-sm text-slate-600">data;descrição;entidade;valor</span>
                </span>
              </button>
            </div>
            <div className="rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
              As contas sugeridas são apoio à classificação e devem ser validadas por contabilista certificado antes
              de qualquer lançamento oficial.
            </div>
            <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm leading-6 text-blue-900">
              Base de conformidade: SNC Portugal como referência de classificação, RGPD para dados pessoais e
              transparência de IA. O SEO não efetua lançamentos contabilísticos oficiais sem validação humana.
            </div>
          </div>
        </Panel>

        <Panel title="Resumo contabilístico" action="Exportar" onAction={onExport}>
          <div className="grid gap-3 sm:grid-cols-3">
            <MiniStat label="Movimentos" value={String(movements.length)} />
            <MiniStat label="Confiança média" value={`${averageConfidence}%`} />
            <MiniStat label="Contas usadas" value={String(new Set(movements.map((item) => item.accountCode)).size)} />
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-4 text-sm font-semibold text-emerald-800">90%+ · {highConfidence}</div>
            <div className="rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm font-semibold text-amber-900">70-89% · {mediumConfidence}</div>
            <div className="rounded-lg border border-red-100 bg-red-50 p-4 text-sm font-semibold text-red-800">&lt;70% · {lowConfidence}</div>
          </div>
          <button className="mt-4 w-full rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800 hover:bg-emerald-100" type="button">
            Aprovar tudo acima de 90%
          </button>
          <div className="mt-4 grid gap-3">
            <div className="rounded-lg border border-line bg-mist p-4">
              <p className="text-sm font-medium text-slate-500">Débitos sugeridos</p>
              <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(totalDebit)}</p>
            </div>
            <div className="rounded-lg border border-line bg-mist p-4">
              <p className="text-sm font-medium text-slate-500">Créditos sugeridos</p>
              <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(totalCredit)}</p>
            </div>
          </div>
        </Panel>
      </section>

      {selectedMovement && (
        <section className="rounded-[28px] border border-blue-100 bg-white p-6 shadow-[0_18px_60px_rgba(0,0,0,0.06)]">
          <div className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#0071e3]">Reclassificação manual</p>
              <h3 className="mt-2 text-2xl font-semibold tracking-tight text-[#1d1d1f]">Primeiro escolha a conta SNC correta</h3>
              <p className="mt-3 text-sm leading-6 text-[#6e6e73]">
                A nova conta substitui a sugestão da IA, atualiza o ficheiro exportável e recalcula vendas, despesas, lucro, margem, gráficos e dashboard.
              </p>
              <div className="mt-4 rounded-2xl bg-[#f5f5f7] p-4">
                <p className="text-sm font-semibold text-[#1d1d1f]">{selectedMovement.description}</p>
                <p className="mt-1 text-sm text-[#6e6e73]">
                  {selectedMovement.entity} · {formatCurrency(selectedMovement.amount)} · conta atual {selectedMovement.accountCode} - {selectedMovement.accountName}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-black/10 bg-[#fbfbfd] p-5">
              <label className="text-sm font-semibold text-[#1d1d1f]" htmlFor="snc-account">
                Qual conta?
              </label>
              <select
                id="snc-account"
                className="mt-2 h-12 w-full rounded-xl border border-black/10 bg-white px-3 text-sm text-[#1d1d1f] outline-none focus:border-[#0071e3]"
                value={selectedAccountCode}
                onChange={(event) => setSelectedAccountCode(event.target.value)}
              >
                {accountRules.map((account) => (
                  <option key={account.code} value={account.code}>
                    {account.code} - {account.name}
                  </option>
                ))}
              </select>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                <button
                  className="h-11 rounded-xl bg-[#0071e3] px-4 text-sm font-semibold text-white hover:bg-[#0077ed]"
                  onClick={() => {
                    onReclassify(selectedMovement.id, selectedAccountCode);
                    setSelectedMovementId(null);
                  }}
                  type="button"
                >
                  Aplicar e recalcular
                </button>
                <button
                  className="h-11 rounded-xl border border-black/10 bg-white px-4 text-sm font-semibold text-[#1d1d1f] hover:bg-[#f5f5f7]"
                  onClick={() => setSelectedMovementId(null)}
                  type="button"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </section>
      )}

      <Panel title="Movimentos classificados por conta SNC" action="Exportar Excel atualizado" onAction={onExport}>
        {movements.length === 0 ? (
          <div className="rounded-lg border border-line bg-mist p-6 text-sm text-slate-600">
            Ainda não existem movimentos classificados. Importe um ficheiro para iniciar a classificação.
          </div>
        ) : (
          <div className="scrollbar-thin overflow-x-auto">
            <table className="w-full min-w-[980px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-line bg-mist">
                  {["Data", "Descrição", "Entidade", "Valor", "Conta SNC", "Tipo", "Confiança", "Justificação", "Ação"].map((column) => (
                    <th key={column} className="px-3 py-3 font-semibold text-slate-600">
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {movements.map((movement) => {
                  const confidenceClass =
                    movement.confidence >= 90
                      ? "bg-emerald-50 text-emerald-700"
                      : movement.confidence >= 70
                        ? "bg-amber-50 text-amber-800"
                        : "bg-red-50 text-red-700";
                  return (
                    <tr key={movement.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-3 py-3 text-slate-700">{movement.date}</td>
                      <td className="max-w-64 px-3 py-3 text-slate-700">{movement.description}</td>
                      <td className="px-3 py-3 text-slate-700">{movement.entity}</td>
                      <td className="px-3 py-3 font-semibold text-slate-900">{formatCurrency(movement.amount)}</td>
                      <td className="px-3 py-3 text-slate-700">{movement.accountCode} - {movement.accountName}</td>
                      <td className="px-3 py-3 text-slate-700">{movement.movementType}</td>
                      <td className="px-3 py-3">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${confidenceClass}`}>
                          {movement.confidence}%
                        </span>
                      </td>
                      <td className="max-w-72 px-3 py-3 text-slate-700">{movement.reason}</td>
                      <td className="px-3 py-3">
                        <button
                          className="rounded-lg border border-line px-3 py-1.5 text-xs font-semibold text-navy-800 hover:bg-mist"
                          onClick={() => {
                            setSelectedMovementId(movement.id);
                            setSelectedAccountCode(movement.accountCode);
                          }}
                          type="button"
                        >
                          Reclassificar
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}

function CloudBillingView({
  period,
  reportDate,
  snapshots,
  comparison,
  subscription,
  files,
  onPeriodChange,
  onReportDateChange,
  onRefresh,
  onCreateSnapshot,
  onCheckout,
  onDownloadFile,
}: {
  period: SnapshotPeriod;
  reportDate: string;
  snapshots: MetricSnapshot[];
  comparison: SnapshotComparison | null;
  subscription: BillingSubscription | null;
  files: CloudFile[];
  onPeriodChange: (period: SnapshotPeriod) => void;
  onReportDateChange: (date: string) => void;
  onRefresh: () => void;
  onCreateSnapshot: () => void;
  onCheckout: (plan: string) => void;
  onDownloadFile: (file: CloudFile) => void;
}) {
  const periods: Array<{ id: SnapshotPeriod; label: string }> = [
    { id: "daily", label: "Diário" },
    { id: "weekly", label: "Semanal" },
    { id: "monthly", label: "Mensal" },
    { id: "quarterly", label: "Trimestral" },
    { id: "annual", label: "Anual" },
  ];
  const delta = comparison?.delta ?? {};
  const current = comparison?.current ?? snapshots[0]?.metrics ?? {};
  const totalStorage = files.reduce((sum, file) => sum + file.sizeBytes, 0);
  const formats = new Set(files.map((file) => file.filename.split(".").pop()?.toUpperCase()).filter(Boolean));
  const latestFile = files[0];
  const storageLabel = totalStorage >= 1024 * 1024 ? `${(totalStorage / (1024 * 1024)).toFixed(1)} MB` : `${(totalStorage / 1024).toFixed(1)} KB`;

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <MetricCard icon={Cloud} label="Ficheiros guardados" value={String(files.length)} delta={`${snapshots.length} snapshots`} tone="navy" />
        <MetricCard icon={Download} label="Armazenamento" value={storageLabel} delta={`${formats.size} formatos`} tone="navy" />
        <MetricCard icon={ShieldCheck} label="SEO Core" value={String(current.seo_index ?? "-")} delta="comparável" tone="success" />
        <MetricCard icon={AlertTriangle} label="Delta risco" value={String(delta.capital_at_risk ?? 0)} delta="capital em risco" tone="warning" />
        <MetricCard icon={CreditCard} label="Subscrição" value={subscription?.status ?? "trial"} delta={subscription?.plan ?? "starter"} tone="navy" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel title="Histórico em nuvem" action="Atualizar" onAction={onRefresh}>
          <div className="mb-5 rounded-2xl border border-[#d9e2ec] bg-[#f8fafc] p-4">
            <label className="flex items-center gap-3 text-sm font-semibold text-[#1d1d1f]" htmlFor="report-date">
              <CalendarDays size={19} className="text-[#0071e3]" /> Calendário de relatórios diários
            </label>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
              <input
                id="report-date"
                type="date"
                value={reportDate}
                max="2099-12-31"
                onChange={(event) => onReportDateChange(event.target.value)}
                className="h-11 rounded-xl border border-black/10 bg-white px-4 text-sm text-[#1d1d1f]"
              />
              <p className="text-xs leading-5 text-slate-500">Selecione um dia para consultar ou guardar o respetivo relatório no histórico da nuvem.</p>
            </div>
          </div>
          <div className="mb-4 flex flex-wrap gap-2">
            {periods.map((item) => (
              <button
                key={item.id}
                className={`rounded-full border px-4 py-2 text-sm font-semibold ${
                  period === item.id ? "border-[#0071e3] bg-[#0071e3] text-white" : "border-black/10 bg-white text-[#1d1d1f]"
                }`}
                onClick={() => onPeriodChange(item.id)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
          <button
            className="mb-5 inline-flex h-10 items-center gap-2 rounded-full bg-[#1d1d1f] px-5 text-sm font-semibold text-white hover:bg-black"
            onClick={onCreateSnapshot}
            type="button"
          >
            <Cloud size={17} aria-hidden="true" />
            Guardar relatório diário
          </button>
          {comparison?.message ? (
            <div className="rounded-lg border border-line bg-mist p-4 text-sm text-slate-700">{comparison.message}</div>
          ) : (
            <DataTable
              columns={["Indicador", "Atual", "Anterior", "Diferença"]}
              rows={[
                ["Índice SEO", String(comparison?.current.seo_index ?? "-"), String(comparison?.previous?.seo_index ?? "-"), String(delta.seo_index ?? 0)],
                [
                  "Capital em risco",
                  formatCurrency(Number(comparison?.current.capital_at_risk ?? 0)),
                  formatCurrency(Number(comparison?.previous?.capital_at_risk ?? 0)),
                  formatCurrency(Number(delta.capital_at_risk ?? 0)),
                ],
                ["Pendências", String(comparison?.current.unresolved_issues ?? "-"), String(comparison?.previous?.unresolved_issues ?? "-"), String(delta.unresolved_issues ?? 0)],
                ["Produtos parados", String(comparison?.current.stalled_products ?? "-"), String(comparison?.previous?.stalled_products ?? "-"), String(delta.stalled_products ?? 0)],
              ]}
            />
          )}
        </Panel>

        <Panel title="Pagamento e planos" action="Ver estado" onAction={onRefresh}>
          <div className="mb-4 rounded-lg border border-line bg-mist p-4">
            <p className="text-sm font-semibold text-ink">Estado atual</p>
            <p className="mt-1 text-sm text-slate-600">
              Plano {subscription?.plan ?? "starter"} · {subscription?.status ?? "trial"}
            </p>
          </div>
          <div className="grid gap-3">
            {[
              ["starter", "Starter", "Histórico essencial e relatórios PDF"],
              ["professional", "Professional", "Snapshots completos, IA e conciliação"],
              ["business", "Business", "Várias empresas, auditoria e suporte prioritário"],
            ].map(([plan, title, detail]) => (
              <button
                key={plan}
                className="flex items-center justify-between gap-4 rounded-lg border border-line bg-white p-4 text-left hover:bg-mist"
                onClick={() => onCheckout(plan)}
                type="button"
              >
                <span>
                  <span className="block text-sm font-semibold text-ink">{title}</span>
                  <span className="mt-1 block text-sm text-slate-600">{detail}</span>
                </span>
                <CreditCard size={20} className="text-[#0071e3]" aria-hidden="true" />
              </button>
            ))}
          </div>
        </Panel>
      </section>

      <Panel title="Arquivo documental na nuvem" action="Atualizar" onAction={onRefresh}>
        <div className="mb-5 grid gap-3 rounded-2xl bg-[#f5f5f7] p-4 md:grid-cols-3">
          <MiniStat label="Formatos disponíveis" value={formats.size ? Array.from(formats).join(" · ") : "—"} />
          <MiniStat label="Último carregamento" value={latestFile ? new Date(latestFile.uploadedAt).toLocaleDateString("pt-PT") : "—"} />
          <MiniStat label="Integridade" value={files.length ? "SHA-256 verificada" : "A aguardar dados"} />
        </div>
        {files.length === 0 ? (
          <div className="rounded-lg border border-dashed border-line bg-mist p-6 text-center text-sm text-slate-600">
            Os Excel, PDF, CSV, TXT e SAF-T carregados aparecerão aqui, guardados integralmente e associados à empresa.
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {files.map((file) => (
              <button key={file.id} className="rounded-xl border border-line bg-white p-4 text-left transition hover:border-[#0071e3] hover:bg-blue-50/30" onClick={() => onDownloadFile(file)} type="button">
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-[#0071e3]"><FileSpreadsheet size={19} aria-hidden="true" /></span>
                  <Download size={17} className="text-slate-500" aria-hidden="true" />
                </div>
                <p className="mt-3 truncate text-sm font-semibold text-ink">{file.filename}</p>
                <p className="mt-1 text-xs text-slate-500">{file.category} · {(file.sizeBytes / 1024).toFixed(1)} KB</p>
                <p className="mt-1 text-xs text-slate-500">{new Date(file.uploadedAt).toLocaleString("pt-PT")}</p>
                <p className="mt-2 truncate font-mono text-[10px] text-slate-400">SHA-256 {file.sha256}</p>
              </button>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Histórico diário de relatórios" action="Guardar hoje" onAction={onCreateSnapshot}>
        <DataTable
          columns={["Dia do relatório", "Guardado em", "Etiqueta", "SEO", "Capital em risco"]}
          rows={snapshots.map((snapshot) => [
            new Date(`${snapshot.reportDate}T12:00:00`).toLocaleDateString("pt-PT"),
            new Date(snapshot.createdAt).toLocaleString("pt-PT"),
            snapshot.label,
            String(snapshot.metrics.seo_index ?? "-"),
            formatCurrency(Number(snapshot.metrics.capital_at_risk ?? 0)),
          ])}
        />
      </Panel>
    </>
  );
}

function StrategyExecutionView({
  unresolvedIssues,
  stalledProducts,
  activeDebts,
  snapshotsCount,
  summary,
  onGoTo,
}: {
  unresolvedIssues: number;
  stalledProducts: number;
  activeDebts: number;
  snapshotsCount: number;
  summary: (typeof periodData)[keyof typeof periodData];
  onGoTo: (section: SectionId) => void;
}) {
  const activeSignals: StrategySignal[] = [
    "financialImpact",
    "recurringPain",
    "decisionAutomation",
    "securityTrust",
    "simpleProduct",
    ...(snapshotsCount > 0 ? (["proprietaryData"] as StrategySignal[]) : []),
    ...(summary.sales > 0 ? (["saasRevenue"] as StrategySignal[]) : []),
  ];
  const fit = scoreStrategyFit(activeSignals);
  const capitalAtRisk = activeDebts * 190 + stalledProducts * 75 + unresolvedIssues * 320;

  return (
    <>
      <section className="overflow-hidden rounded-[32px] bg-white shadow-[0_24px_80px_rgba(0,0,0,0.08)]">
        <div className="border-b border-black/5 bg-[#fbfbfd] px-5 py-7 md:px-7">
          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-[#f5f5f7] px-4 py-2 text-sm font-semibold text-[#0071e3]">
                <Target size={16} aria-hidden="true" />
                Processo de escala
              </div>
              <h3 className="mt-4 text-3xl font-semibold tracking-tight text-[#1d1d1f] md:text-4xl">
                Construir so o que gera decisao de lucro
              </h3>
              <p className="mt-3 max-w-4xl text-sm leading-6 text-[#6e6e73] md:text-base">{strategyNorthStar}</p>
            </div>
            <div className="rounded-[28px] bg-[#1d1d1f] p-5 text-white">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-white/60">Ajuste estrategico</p>
              <p className="mt-3 text-5xl font-semibold">{fit.score}%</p>
              <p className="mt-2 text-sm text-white/70">{fit.decision}</p>
              <div className="mt-5 rounded-2xl bg-white/10 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-white/60">Capital em risco detectado</p>
                <p className="mt-2 text-2xl font-semibold">{formatCurrency(capitalAtRisk)}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-3 bg-white p-5 md:grid-cols-4 md:p-6">
          <button
            className="rounded-lg border border-line bg-mist px-4 py-3 text-left text-sm font-semibold text-ink hover:bg-white"
            onClick={() => onGoTo("dashboard")}
            type="button"
          >
            Ver dinheiro em risco
          </button>
          <button
            className="rounded-lg border border-line bg-mist px-4 py-3 text-left text-sm font-semibold text-ink hover:bg-white"
            onClick={() => onGoTo("nuvem")}
            type="button"
          >
            Guardar historico
          </button>
          <button
            className="rounded-lg border border-line bg-mist px-4 py-3 text-left text-sm font-semibold text-ink hover:bg-white"
            onClick={() => onGoTo("ia")}
            type="button"
          >
            Automatizar decisao
          </button>
          <button
            className="rounded-lg border border-line bg-mist px-4 py-3 text-left text-sm font-semibold text-ink hover:bg-white"
            onClick={() => onGoTo("financeiro")}
            type="button"
          >
            Provar ROI
          </button>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Euro} label="Impacto mensal" value={formatCurrency(capitalAtRisk)} delta="perdas a atacar" tone="danger" />
        <MetricCard icon={Cloud} label="Dados proprios" value={String(snapshotsCount)} delta="snapshots guardados" tone="navy" />
        <MetricCard icon={BrainCircuit} label="Decisoes" value={String(unresolvedIssues + stalledProducts + activeDebts)} delta="sinais acionaveis" tone="warning" />
        <MetricCard icon={CreditCard} label="SaaS" value={fit.decision} delta={`${fit.score}% alinhado`} tone="success" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Pilares codificados" action="Ir para IA" onAction={() => onGoTo("ia")}>
          <div className="grid gap-3">
            {strategyPillars.map((pillar) => {
              const active = activeSignals.includes(pillar.id);
              return (
                <div key={pillar.id} className="rounded-lg border border-line bg-white p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-ink">{pillar.title}</p>
                      <p className="mt-1 text-sm leading-5 text-slate-600">{pillar.question}</p>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${active ? "bg-emerald-50 text-success" : "bg-amber-50 text-warning"}`}>
                      {active ? "ativo" : "reforcar"}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">{pillar.outcome}</p>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel title="Processo para construir" action="Histórico" onAction={() => onGoTo("nuvem")}>
          <div className="space-y-3">
            {strategyProcessSteps.map((step, index) => (
              <div key={step.title} className="rounded-lg border border-line bg-mist p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#0071e3]">Passo {index + 1}</p>
                <p className="mt-2 text-sm font-semibold text-ink">{step.title}</p>
                <p className="mt-1 text-sm text-slate-600">{step.action}</p>
                <p className="mt-2 text-xs text-slate-500">{step.evidence}</p>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Planos SaaS" action="Pagamentos" onAction={() => onGoTo("nuvem")}>
          <DataTable columns={["Plano", "Cliente", "Valor"]} rows={saasPlanStrategy.map((plan) => [plan.plan, plan.customer, plan.value])} />
        </Panel>

        <Panel title="Roadmap de escala" action="Centro" onAction={() => onGoTo("dashboard")}>
          <div className="grid gap-3">
            {roadmapStages.map((stage) => (
              <div key={stage.phase} className="rounded-lg border border-line bg-white p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-ink">
                    {stage.phase} · {stage.title}
                  </p>
                  <span className="rounded-full bg-mist px-3 py-1 text-xs font-semibold text-slate-600">
                    {stage.outcomes.length} entregas
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {stage.outcomes.map((outcome) => (
                    <span key={outcome} className="rounded-full border border-line px-3 py-1 text-xs text-slate-600">
                      {outcome}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </section>
    </>
  );
}

function DocumentIntelligenceView({
  intelligence,
  onUpload,
  onOpenIssues,
  ocrResult,
  readingDocument,
  ocrError,
  onReadDocument,
}: {
  intelligence: DocumentIntelligence | null;
  onUpload: () => void;
  onOpenIssues: () => void;
  ocrResult: OcrResult | null;
  readingDocument: boolean;
  ocrError: string;
  onReadDocument: (file: File) => void | Promise<void>;
}) {
  const ocrInputRef = useRef<HTMLInputElement>(null);
  const ocrPanel = (
    <Panel title="Leitura completa por OCR" action={readingDocument ? "A ler…" : "Selecionar PDF ou imagem"} onAction={() => !readingDocument && ocrInputRef.current?.click()}>
      <input ref={ocrInputRef} className="hidden" type="file" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff,.webp,application/pdf,image/*" onChange={(event) => { const file = event.target.files?.[0]; if (file) void onReadDocument(file); event.currentTarget.value = ""; }} />
      {readingDocument && <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5 text-sm text-blue-900"><span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-blue-600" />A ler o ficheiro completo, página por página…</div>}
      {ocrError && !readingDocument && <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{ocrError}</div>}
      {!ocrResult && !readingDocument && !ocrError && <div className="rounded-2xl border border-dashed border-slate-300 bg-mist p-7 text-center"><Files className="mx-auto text-[#0071e3]" size={32} /><p className="mt-3 font-semibold text-ink">PDF ou imagem com várias páginas</p><p className="mt-2 text-sm text-slate-600">Lê texto incorporado e aplica OCR local apenas nas páginas digitalizadas. Limite: 25 MB.</p></div>}
      {ocrResult && !readingDocument && <div className="space-y-4"><div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4"><div><p className="font-semibold text-emerald-950">{ocrResult.filename}</p><p className="mt-1 text-sm text-emerald-800">{ocrResult.page_count} página(s) · leitura completa</p></div><CheckCircle2 className="text-emerald-600" size={24} /></div><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{ocrResult.pages.map((page) => <div key={page.page} className="rounded-xl border border-line bg-white p-3"><p className="text-sm font-semibold text-ink">Página {page.page}</p><p className="mt-1 text-xs text-slate-600">{page.method === "embedded_text" ? "Texto incorporado" : "OCR local"} · {page.text.length} caracteres</p></div>)}</div><details className="rounded-2xl border border-line bg-white p-4"><summary className="cursor-pointer text-sm font-semibold text-ink">Ver texto completo extraído</summary><pre className="mt-4 max-h-96 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-4 text-xs leading-5 text-slate-100">{ocrResult.full_text}</pre></details></div>}
    </Panel>
  );
  if (!intelligence) {
    return (
      <div className="space-y-6">{ocrPanel}<Panel title="Inteligência documental" action="Carregar ficheiro" onAction={onUpload}>
        <div className="rounded-2xl border border-dashed border-slate-300 bg-mist p-10 text-center">
          <Files className="mx-auto text-[#0071e3]" size={36} aria-hidden="true" />
          <p className="mt-4 font-semibold text-ink">Carregue documentos para classificar e validar</p>
          <p className="mt-2 text-sm text-slate-600">Excel, CSV, TXT e XML/SAF-T são processados com rastreabilidade.</p>
        </div>
      </Panel></div>
    );
  }

  return (
    <>
      {ocrPanel}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <MetricCard icon={Files} label="Processados" value={String(intelligence.stats.processed)} delta={intelligence.sourceFormat} tone="navy" />
        <MetricCard icon={CheckCircle2} label="Validados" value={String(intelligence.stats.valid)} delta="sem alertas" tone="success" />
        <MetricCard icon={Sparkles} label="Corrigidos pela IA" value={String(intelligence.stats.corrected ?? 0)} delta="cálculos refeitos" tone="success" />
        <MetricCard icon={AlertTriangle} label="Revisão humana" value={String(intelligence.stats.review)} delta="requer atenção" tone="warning" />
        <MetricCard icon={ClipboardCheck} label="Duplicados" value={String(intelligence.stats.duplicates)} delta="possíveis casos" tone="danger" />
        <MetricCard icon={Clock3} label="Vencidos" value={String(intelligence.stats.overdue)} delta="prioridade financeira" tone="danger" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <Panel title="Documentos interpretados" action="Novo processamento" onAction={onUpload}>
          <DataTable
            columns={["Documento", "Tipo", "Entidade", "Estado", "Total", "Confiança", "Validação"]}
            rows={intelligence.documents.slice(0, 100).map((document) => [
              document.number,
              document.documentType,
              document.entity,
              document.financialState,
              formatCurrency(document.totalAmount),
              `${document.confidence}%`,
              document.validations[0] ?? "Validado",
            ])}
          />
        </Panel>

        <div className="space-y-6">
          <Panel title="Totais contabilísticos" action="Ver alertas" onAction={onOpenIssues}>
            <div className="grid gap-3">
              <MiniStat label="Valor sem IVA" value={formatCurrency(intelligence.totals.net)} />
              <MiniStat label="IVA" value={formatCurrency(intelligence.totals.vat)} />
              <MiniStat label="Total" value={formatCurrency(intelligence.totals.total)} />
            </div>
            <p className="mt-4 rounded-lg bg-amber-50 p-3 text-xs leading-5 text-amber-900">Notas de crédito são normalizadas como valores negativos. Resultados fiscais exigem validação por contabilista certificado.</p>
          </Panel>
          <Panel title="Rastreabilidade" action="Auditoria ativa">
            <div className="space-y-3">
              {intelligence.auditTrail.map((entry, index) => (
                <div key={entry} className="flex gap-3 text-sm text-slate-600">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-[#0071e3]">{index + 1}</span>
                  <p>{entry}</p>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </section>
    </>
  );
}

function AiView({
  question,
  analysis,
  onQuestionChange,
  onAsk,
  onAttach,
  generatedFiles,
  rowErrors,
  onDownloadGeneratedFile,
  onNewConversation,
}: {
  question: string;
  analysis: AiAnalysis;
  onQuestionChange: (question: string) => void;
  onAsk: (submittedQuestion: string, analysisLevel?: string) => AiAnalysis | void | Promise<AiAnalysis | void>;
  onAttach: (file: File | undefined, signal?: AbortSignal) => ImportedDataset | void | Promise<ImportedDataset | void>;
  generatedFiles: CloudFile[];
  rowErrors: Array<{ row: number; document: string; errors: string[] }>;
  onDownloadGeneratedFile: (file: CloudFile) => void | Promise<void>;
  onNewConversation: () => void;
}) {
  const [assistantMode, setAssistantMode] = useState<"chat" | "work">("chat");
  const [analysisLevel, setAnalysisLevel] = useState("Elevado");
  const [hasAsked, setHasAsked] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachmentStatus, setAttachmentStatus] = useState<"idle" | "processing" | "ready" | "error">("idle");
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const [conversationDate, setConversationDate] = useState<Date | null>(null);
  const [responseDate, setResponseDate] = useState<Date | null>(null);
  const [conversationHistory, setConversationHistory] = useState<Array<{ question: string; at: Date }>>([]);
  const [pastTurns, setPastTurns] = useState<Array<{ question: string; answer: string; at: Date; responseAt: Date; fileName?: string }>>([]);
  const [lastSubmittedQuestion, setLastSubmittedQuestion] = useState("");
  const [processingProgress, setProcessingProgress] = useState(0);
  const [workSteps, setWorkSteps] = useState<Array<{ label: string; state: "pending" | "running" | "done" }>>([]);
  const [lastWorkResult, setLastWorkResult] = useState<ImportedDataset | null>(null);
  const processingControllerRef = useRef<AbortController | null>(null);
  const assistantFileRef = useRef<HTMLInputElement>(null);
  const suggestions = [
    ["Analisar documentos", "Separe faturas, faturas-recibo e notas de crédito"],
    ["Organizar inventário", "Compare o stock físico com o sistema"],
    ["Ver pagamentos", "Mostre as faturas vencidas e os clientes em atraso"],
    ["Separar faturação", "Organize Coimbra e Picoto, exclua anulados e calcule os totais"],
  ];

  const submitQuestion = async (questionOverride?: string) => {
    const submittedQuestion = (questionOverride ?? question).trim();
    if (!submittedQuestion || isSending) return;
    const submittedAt = new Date();
    if (responseDate && lastSubmittedQuestion) {
      setPastTurns((turns) => [...turns, {
        question: lastSubmittedQuestion,
        answer: analysis.answer,
        at: conversationDate ?? responseDate,
        responseAt: responseDate,
        fileName: attachmentStatus === "ready" ? attachedFile?.name : undefined,
      }].slice(-20));
    }
    setLastSubmittedQuestion(submittedQuestion);
    setConversationDate(submittedAt);
    setConversationHistory((current) => [...current, { question: submittedQuestion, at: submittedAt }].slice(-10));
    setHasAsked(true);
    setIsSending(true);
    setResponseDate(null);
    setSendError("");
    if (!attachedFile || attachmentStatus === "ready") {
      setWorkSteps([]);
      setProcessingProgress(0);
    }
    try {
      if (attachedFile && attachmentStatus !== "ready") {
        const processed = await processAttachedFile();
        if (!processed) return;
        setResponseDate(new Date());
        onQuestionChange("");
        return;
      }
      await onAsk(submittedQuestion, analysisLevel);
      setResponseDate(new Date());
      onQuestionChange("");
    } catch (error) {
      setSendError(error instanceof Error ? error.message : "Não foi possível obter uma resposta. Tente novamente.");
    } finally {
      setIsSending(false);
    }
  };

  const startNewConversation = () => {
    setHasAsked(false);
    setLastSubmittedQuestion("");
    setConversationDate(null);
    setResponseDate(null);
    setAttachedFile(null);
    setAttachmentStatus("idle");
    setSendError("");
    setWorkSteps([]);
    setLastWorkResult(null);
    setPastTurns([]);
    onQuestionChange("");
    onNewConversation();
  };

  const attachFile = async (file: File | undefined) => {
    if (!file) return;
    setAttachedFile(file);
    setAttachmentStatus("idle");
    setLastWorkResult(null);
    const isImage = file.type.startsWith("image/");
    onQuestionChange(isImage
      ? `Analise a imagem ${file.name} e identifique informação operacional relevante.`
      : `Analise o ficheiro ${file.name}, organize os dados, faça os cálculos necessários e indique anomalias.`);
  };

  const processAttachedFile = async () => {
    if (!attachedFile || attachmentStatus === "processing") return false;
    setAttachmentStatus("processing");
    setProcessingProgress(5);
    setWorkSteps([
      { label: "Ler e validar o ficheiro", state: "running" },
      { label: "Aplicar as regras pedidas", state: "pending" },
      { label: "Verificar cálculos e anomalias", state: "pending" },
      { label: "Gerar e guardar o resultado", state: "pending" },
    ]);
    setSendError("");
    const controller = new AbortController();
    processingControllerRef.current = controller;
    const progressTimer = window.setInterval(() => setProcessingProgress((value) => {
      const next = Math.min(90, value + (value < 40 ? 9 : 3));
      const activeIndex = next < 28 ? 0 : next < 52 ? 1 : next < 76 ? 2 : 3;
      setWorkSteps((steps) => steps.map((step, index) => ({ ...step, state: index < activeIndex ? "done" : index === activeIndex ? "running" : "pending" })));
      return next;
    }), 350);
    try {
      const result = await onAttach(attachedFile, controller.signal);
      window.clearInterval(progressTimer);
      setProcessingProgress(100);
      setWorkSteps((steps) => steps.map((step) => ({ ...step, state: "done" })));
      if (result) setLastWorkResult(result);
      setAttachmentStatus("ready");
      return true;
    } catch (error) {
      window.clearInterval(progressTimer);
      if (error instanceof DOMException && error.name === "AbortError") {
        setAttachmentStatus("idle");
        setProcessingProgress(0);
        setSendError("Processamento cancelado pelo utilizador.");
        return false;
      }
      setAttachmentStatus("error");
      setSendError(error instanceof Error ? error.message : "Não foi possível processar o anexo.");
      return false;
    } finally {
      processingControllerRef.current = null;
    }
  };

  return (
    <section className="mx-auto grid min-h-[calc(100vh-12rem)] w-full max-w-7xl gap-4 text-white lg:grid-cols-[240px_1fr]">
      <aside className="hidden rounded-3xl border border-white/10 bg-white/[0.025] p-3 lg:flex lg:flex-col">
        <button type="button" onClick={startNewConversation} className="flex items-center gap-3 rounded-xl border border-white/10 px-4 py-3 text-left text-sm font-semibold transition hover:bg-white/[0.06]"><Plus size={18} />Nova conversa</button>
        <p className="mt-6 px-2 text-[11px] font-semibold uppercase tracking-[0.15em] text-[#78716c]">Conversas recentes</p>
        <div className="mt-2 space-y-1">
          {conversationHistory.length === 0 ? <p className="px-2 py-3 text-xs leading-5 text-[#78716c]">As conversas desta sessão aparecem aqui.</p> : conversationHistory.slice().reverse().map((entry, index) => (
            <button key={`${entry.at.toISOString()}-${index}`} type="button" onClick={() => onQuestionChange(entry.question)} className="w-full truncate rounded-xl px-3 py-2.5 text-left text-sm text-[#d6d3d1] hover:bg-white/[0.06]" title={entry.question}>{entry.question}</button>
          ))}
        </div>
        <div className="mt-auto rounded-2xl border border-white/10 bg-black/20 p-3 text-xs leading-5 text-[#a8a29e]"><span className="font-semibold text-white">SEO Assistente</span><br />Faturação, pagamentos e inventário com dados da empresa.</div>
      </aside>

      <div className="flex min-w-0 flex-col">
      <div className="mx-auto flex rounded-full bg-white/[0.06] p-1">
        {(["chat", "work"] as const).map((mode) => (
          <button key={mode} type="button" onClick={() => setAssistantMode(mode)} className={`min-w-32 rounded-full px-8 py-3 text-sm font-semibold transition ${assistantMode === mode ? "bg-white/[0.08] text-white" : "text-[#a38476] hover:text-white"}`}>
            {mode === "chat" ? "Chat" : "Trabalho"}
          </button>
        ))}
      </div>

      <div className={`flex flex-1 flex-col py-8 ${hasAsked ? "justify-between" : "justify-center"}`}>
        {!hasAsked ? (
          <div className="mb-10 text-center">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-amber-400">Assistente operacional</p>
            <h1 className="text-3xl font-medium tracking-tight md:text-4xl">Como posso ajudar hoje?</h1>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-[#a8a29e]">Analiso faturação, pagamentos e inventário, organizo ficheiros e apresento resultados prontos para decisão.</p>
          </div>
        ) : (
          <div className="mb-8 space-y-5">
            {pastTurns.map((turn, index) => (
              <div key={`${turn.at.toISOString()}-${index}`} className="space-y-4 border-b border-white/10 pb-6">
                <div className="ml-auto max-w-2xl">
                  {turn.fileName && <div className="mb-2 ml-auto flex w-fit items-center gap-2 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs text-[#d6d3d1]"><FileSpreadsheet size={15} className="text-emerald-400" />{turn.fileName}</div>}
                  <div className="rounded-3xl bg-[#242424] px-5 py-4 text-sm leading-6">{turn.question}</div>
                  <p className="mt-1 text-right text-[11px] text-[#78716c]">{turn.at.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}</p>
                </div>
                <div className="max-w-3xl px-2">
                  <div className="mb-2 flex items-center gap-2 text-sm font-semibold"><Bot size={16} className="text-amber-400" />SEO Assistente</div>
                  <p className="text-sm leading-7 text-[#d6d3d1]">{turn.answer}</p>
                  <p className="mt-2 text-[11px] text-[#78716c]">{turn.responseAt.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}</p>
                </div>
              </div>
            ))}
            {conversationDate && (
              <div className="flex items-center justify-center gap-2 text-xs text-[#78716c]">
                <span className="h-px flex-1 bg-white/10" />
                <CalendarDays size={14} />
                {conversationDate.toLocaleDateString("pt-PT", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })}
                <span className="h-px flex-1 bg-white/10" />
              </div>
            )}
            <div className="ml-auto max-w-2xl">
              {attachedFile && <div className="mb-2 ml-auto flex w-fit max-w-full items-center gap-3 rounded-2xl border border-white/15 bg-black/30 px-4 py-3"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500 text-white"><FileSpreadsheet size={21} /></span><span className="min-w-0"><strong className="block truncate text-sm text-white">{attachedFile.name}</strong><span className="text-xs text-[#a8a29e]">{attachedFile.type.startsWith("image/") ? "Imagem" : attachedFile.name.toLowerCase().endsWith(".pdf") ? "Documento PDF" : "Folha de cálculo"} · {(attachedFile.size / 1024).toFixed(1)} KB</span></span></div>}
              <div className="rounded-3xl bg-[#242424] px-5 py-4 text-sm leading-6 text-white">{lastSubmittedQuestion}</div>
              {conversationDate && <p className="mt-1.5 px-3 text-right text-[11px] text-[#78716c]">Enviado às {conversationDate.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}</p>}
            </div>
            <div className="max-w-3xl px-2">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold"><span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/15 text-amber-400"><Bot size={16} /></span>SEO Assistente</div>
              {isSending ? (
                <div className="space-y-4"><div className="flex items-center gap-3 text-sm text-[#a8a29e]"><span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />A executar o trabalho… {processingProgress > 0 ? `${processingProgress}%` : ""}</div>{workSteps.length > 0 && <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-4"><div className="space-y-3">{workSteps.map((step) => <div key={step.label} className="flex items-center gap-3 text-sm"><span className={`flex h-5 w-5 items-center justify-center rounded-full ${step.state === "done" ? "bg-emerald-500/20 text-emerald-400" : step.state === "running" ? "bg-amber-500/20 text-amber-400" : "bg-white/5 text-[#78716c]"}`}>{step.state === "done" ? <CheckCircle2 size={14} /> : step.state === "running" ? <span className="h-2 w-2 animate-pulse rounded-full bg-current" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}</span><span className={step.state === "pending" ? "text-[#78716c]" : "text-[#d6d3d1]"}>{step.label}</span></div>)}</div></div>}</div>
              ) : sendError ? (
                <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200"><p>{sendError}</p><button type="button" onClick={() => void submitQuestion(lastSubmittedQuestion)} className="mt-3 rounded-full border border-red-300/30 px-3 py-1.5 text-xs font-semibold hover:bg-red-500/10">Tentar novamente</button></div>
              ) : (
                <div className="space-y-4">
                  {lastWorkResult && <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/[0.07] p-4"><p className="font-semibold text-emerald-300">Trabalho concluído</p><ul className="mt-3 space-y-2 text-sm leading-6 text-[#d6d3d1]"><li>• {lastWorkResult.summary.rowsRead} linhas lidas e validadas.</li><li>• {lastWorkResult.documentIntelligence.stats.processed} documentos processados; {lastWorkResult.documentIntelligence.stats.review} requerem revisão.</li>{lastWorkResult.billingTransform && <><li>• {lastWorkResult.billingTransform.excludedNonBilling} documentos GT/não faturáveis e {lastWorkResult.billingTransform.excludedCancelled} anulados removidos.</li><li>• Coimbra e Picoto separados em {Object.keys(lastWorkResult.billingTransform.groups).length} grupos com subtotais.</li></>}<li>• Total apurado: <strong className="text-white">{formatCurrency(lastWorkResult.billingTransform?.totalAmount ?? lastWorkResult.documentIntelligence.totals.total)}</strong>.</li></ul></div>}
                  <p className="text-sm leading-7 text-[#d6d3d1]">{analysis.answer}</p>
                  {(analysis.priorities.length > 0 || analysis.actions.length > 0) && (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {analysis.priorities.length > 0 && <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-400">Prioridades</p><ul className="mt-3 space-y-2 text-sm text-[#d6d3d1]">{analysis.priorities.slice(0, 3).map((item) => <li key={item}>• {item}</li>)}</ul></div>}
                      {analysis.actions.length > 0 && <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-400">Próximas ações</p><div className="mt-3 space-y-2">{analysis.actions.slice(0, 3).map((item) => <button type="button" key={item} onClick={() => void submitQuestion(item)} className="block w-full rounded-xl border border-white/10 px-3 py-2 text-left text-sm text-[#d6d3d1] hover:bg-white/[0.06] hover:text-white">{item} →</button>)}</div></div>}
                    </div>
                  )}
                  {analysis.nextQuestions && analysis.nextQuestions.length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {analysis.nextQuestions.slice(0, 3).map((item) => <button type="button" key={item} onClick={() => void submitQuestion(item)} className="rounded-full border border-white/10 bg-white/[0.025] px-3 py-2 text-xs text-[#d6d3d1] transition hover:bg-white/[0.08] hover:text-white">{item}</button>)}
                    </div>
                  )}
                  {analysis.explainability && (
                    <details className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 text-xs text-[#a8a29e]">
                      <summary className="cursor-pointer font-semibold text-[#d6d3d1]">Como esta resposta foi calculada</summary>
                      <div className="mt-3 space-y-2 leading-5">
                        <p>{analysis.explainability.method}</p>
                        <p><span className="text-white">Fontes:</span> {analysis.explainability.dataSources.join(", ")}.</p>
                        <p><span className="text-white">Sinais:</span> {analysis.explainability.signals.join(" · ")}.</p>
                        <p>{analysis.explainability.humanReview}</p>
                      </div>
                    </details>
                  )}
                </div>
              )}
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-[#a8a29e]"><span>{analysis.confidence}% confiança</span><span>·</span><span>Risco {analysis.risk}</span><span>·</span><span>{analysis.provider === "openai" ? "IA contextual" : "Análise operacional local"}</span><span>·</span><button type="button" onClick={() => navigator.clipboard?.writeText(analysis.answer)} className="hover:text-white">Copiar</button></div>
              {responseDate && !isSending && <p className="mt-2 text-[11px] text-[#78716c]">Resposta gerada em {responseDate.toLocaleDateString("pt-PT")} às {responseDate.toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" })}</p>}
              {generatedFiles.length > 0 && !isSending && <div className="mt-5 space-y-2"><p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-400">Ficheiros gerados nesta conversa</p>{generatedFiles.map((file) => <div key={file.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4"><div><p className="text-sm font-semibold text-emerald-200">{file.filename}</p><p className="mt-1 text-xs text-emerald-100/70">{(file.sizeBytes / 1024).toFixed(1)} KB · guardado na nuvem</p></div><button type="button" onClick={() => void onDownloadGeneratedFile(file)} className="flex items-center gap-2 rounded-full bg-emerald-400 px-4 py-2 text-sm font-semibold text-emerald-950 hover:bg-emerald-300"><Download size={16} />Descarregar</button></div>)}</div>}
              {rowErrors.length > 0 && !isSending && <div className="mt-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4"><p className="text-sm font-semibold text-amber-200">Linhas que precisam de revisão ({rowErrors.length})</p><div className="mt-3 max-h-40 space-y-2 overflow-y-auto text-xs text-amber-100/80">{rowErrors.slice(0, 30).map((error) => <p key={`${error.row}-${error.document}`}>Linha {error.row} · {error.document}: {error.errors.join("; ")}</p>)}</div></div>}
            </div>
          </div>
        )}

        <div className="rounded-[2rem] border border-white/10 bg-[#242424] p-3 shadow-2xl shadow-black/30">
          <input
            ref={assistantFileRef}
            className="hidden"
            type="file"
            accept="image/*,.pdf,.xlsx,.csv,.txt,.xml"
            onChange={(event) => {
              void attachFile(event.target.files?.[0]);
              event.currentTarget.value = "";
            }}
          />
          {attachedFile && (
            <div className="mx-3 mt-2 flex items-center justify-between rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-white">{attachedFile.name}</p>
                <p className="text-xs text-[#a8a29e]">{attachedFile.type || "Ficheiro"} · {(attachedFile.size / 1024).toFixed(1)} KB · {attachmentStatus === "processing" ? "A processar…" : attachmentStatus === "ready" ? "Processado" : attachmentStatus === "error" ? "Erro no processamento" : "Pronto — carregue Enter"}</p>
                {attachmentStatus === "processing" && <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-amber-400 transition-all" style={{ width: `${processingProgress}%` }} /></div>}
              </div>
              <div className="ml-3 flex items-center gap-2">
                {attachmentStatus === "processing" && <button type="button" onClick={() => processingControllerRef.current?.abort()} className="rounded-full border border-red-400/30 px-3 py-1.5 text-xs text-red-200 hover:bg-red-500/10">Cancelar</button>}
                <button type="button" onClick={() => { setAttachedFile(null); setAttachmentStatus("idle"); }} className="rounded-full px-3 py-1 text-xs text-[#a8a29e] hover:bg-white/10 hover:text-white">Remover</button>
              </div>
            </div>
          )}
          <textarea
            className="min-h-14 w-full resize-none border-0 bg-transparent px-4 py-3 text-base text-white outline-none placeholder:text-[#a8a29e]"
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submitQuestion(); }
            }}
            placeholder={assistantMode === "chat" ? "Pergunte sobre faturação, pagamentos ou inventário" : "Descreva o trabalho que pretende executar"}
            aria-label="Mensagem para a Assistente IA"
          />
          <div className="flex items-center justify-between gap-3 px-1 pb-1">
            <button type="button" onClick={() => assistantFileRef.current?.click()} className="flex h-10 w-10 items-center justify-center rounded-full text-[#d6d3d1] hover:bg-white/10" title="Adicionar foto, PDF, Excel ou outro ficheiro"><Plus size={23} /></button>
            <div className="flex items-center gap-2">
              <select value={analysisLevel} onChange={(event) => setAnalysisLevel(event.target.value)} className="border-0 bg-transparent px-2 text-sm text-[#d6d3d1] outline-none" aria-label="Nível de análise">
                <option className="bg-[#242424]" value="Rápido">Rápido</option><option className="bg-[#242424]" value="Elevado">Elevado</option><option className="bg-[#242424]" value="Auditoria">Auditoria</option>
              </select>
              <button type="button" className="flex h-10 w-10 items-center justify-center rounded-full text-[#d6d3d1] hover:bg-white/10" title="Ditado"><Mic size={21} /></button>
              <button type="button" disabled={isSending || !question.trim()} onClick={() => void submitQuestion()} className="flex h-11 w-11 items-center justify-center rounded-full bg-white text-black hover:bg-[#e7e5e4] disabled:cursor-not-allowed disabled:opacity-40" title="Enviar mensagem"><AudioLines size={22} className={isSending ? "animate-pulse" : ""} /></button>
            </div>
          </div>
        </div>

        {!hasAsked && (
          <div className="mt-8 grid gap-2 sm:grid-cols-2">
            {suggestions.map(([label, prompt]) => (
              <button key={label} type="button" onClick={() => void submitQuestion(prompt)} className="flex items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm text-[#d6d3d1] transition hover:bg-white/[0.05] hover:text-white">
                <Sparkles size={18} className="text-[#a38476]" /><span><strong className="block font-medium">{label}</strong><span className="text-xs text-[#78716c]">{prompt}</span></span>
              </button>
            ))}
          </div>
        )}
      </div>
      </div>
    </section>
  );
}

function NavButton({
  item,
  active,
  onClick,
  compact = false,
}: {
  item: { label: string; icon: LucideIcon };
  active: boolean;
  onClick: () => void;
  compact?: boolean;
}) {
  const Icon = item.icon;
  const stateClass = compact
    ? active
      ? "border-black/10 bg-white text-[#1d1d1f] shadow-[0_10px_30px_rgba(0,0,0,0.06)]"
      : "border-black/10 bg-white/60 text-[#6e6e73] hover:bg-white hover:text-[#1d1d1f]"
    : active
      ? "border border-amber-400/30 bg-amber-500/10 text-amber-400"
      : "border border-transparent text-[#a38476] hover:bg-white/[0.04] hover:text-white";

  return (
    <button
      className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition ${compact ? "border" : ""} ${stateClass}`}
      title={item.label}
      onClick={onClick}
      type="button"
    >
      <Icon size={18} aria-hidden="true" />
      <span className="font-medium">{item.label}</span>
    </button>
  );
}

function SeoWordmark({
  variant,
  size,
}: {
  variant: "dark" | "light";
  size: "sidebar" | "header";
}) {
  const isDark = variant === "dark";
  const isLarge = size === "sidebar";
  const shellClass = isDark
    ? "border-white/10 bg-white/[0.06] text-white shadow-[0_18px_45px_rgba(0,0,0,0.22)]"
    : "border-line bg-white text-navy-950 shadow-soft";
  const letterClass = isLarge ? "text-3xl" : "text-2xl";
  const railWidth = isLarge ? "w-11" : "w-9";

  return (
    <div
      className={`inline-flex items-center rounded-xl border px-4 py-3 ${shellClass}`}
      aria-label="SEO - Sistema de Eficiência Operacional"
    >
      <span className={`font-semibold leading-none tracking-[0.06em] ${letterClass}`}>S</span>
      <span className={`mx-3 flex flex-col gap-1.5 ${railWidth}`} aria-hidden="true">
        <span className="h-1 rounded-full bg-current opacity-90" />
        <span className="h-1 rounded-full bg-[#d8b76a]" />
        <span className="h-1 rounded-full bg-current opacity-90" />
      </span>
      <span className={`relative font-semibold leading-none tracking-[0.04em] ${letterClass}`}>
        O
        <span className="absolute -right-1.5 -top-1.5 h-3 w-3 rotate-45 border-r-2 border-t-2 border-[#d8b76a]" />
      </span>
    </div>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  delta,
  tone,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  delta: string;
  tone: MetricTone;
}) {
  const toneMap = {
    navy: "bg-[#1d1d1f] text-white",
    success: "bg-emerald-50 text-success",
    warning: "bg-amber-50 text-warning",
    danger: "bg-orange-50 text-danger",
  };

  return (
    <article className="rounded-[28px] bg-white p-6 shadow-[0_18px_60px_rgba(0,0,0,0.06)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-[#6e6e73]">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-[#1d1d1f]">{value}</p>
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-full ${toneMap[tone]}`}>
          <Icon size={20} aria-hidden="true" />
        </div>
      </div>
      <p className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-[#6e6e73]">
        {tone === "danger" ? (
          <ArrowDownRight size={15} aria-hidden="true" />
        ) : (
          <ArrowUpRight size={15} aria-hidden="true" />
        )}
        {delta}
      </p>
    </article>
  );
}

function Panel({
  title,
  action,
  onAction,
  children,
}: {
  title: string;
  action: string;
  onAction?: () => void;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-[0_18px_60px_rgba(0,0,0,0.06)]">
      <div className="mb-5 flex items-center justify-between gap-3">
        <h3 className="text-base font-semibold text-[#1d1d1f]">{title}</h3>
        <button
          className="rounded-full border border-black/10 px-4 py-2 text-sm font-medium text-[#0071e3] hover:bg-[#f5f5f7]"
          onClick={onAction}
          type="button"
        >
          {action}
        </button>
      </div>
      {children}
    </section>
  );
}

function AlertRow({
  icon: Icon,
  title,
  detail,
  tone,
}: {
  icon: LucideIcon;
  title: string;
  detail: string;
  tone: MetricTone;
}) {
  const toneMap = {
    navy: "bg-blue-50 text-navy-800",
    success: "bg-emerald-50 text-success",
    warning: "bg-amber-50 text-warning",
    danger: "bg-orange-50 text-danger",
  };

  return (
    <div className="flex gap-3 rounded-lg border border-line bg-white p-3">
      <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${toneMap[tone]}`}>
        <Icon size={18} aria-hidden="true" />
      </div>
      <div>
        <p className="text-sm font-semibold text-ink">{title}</p>
        <p className="mt-1 text-sm leading-5 text-slate-600">{detail}</p>
      </div>
    </div>
  );
}

function DecisionPriorityCard({
  priority,
  onAction,
}: {
  priority: DecisionPriority;
  onAction: () => void;
}) {
  const toneMap = {
    navy: {
      border: "border-blue-100",
      soft: "bg-blue-50 text-navy-800",
      dot: "bg-blue-500",
    },
    success: {
      border: "border-emerald-100",
      soft: "bg-emerald-50 text-success",
      dot: "bg-emerald-500",
    },
    warning: {
      border: "border-amber-100",
      soft: "bg-amber-50 text-warning",
      dot: "bg-amber-500",
    },
    danger: {
      border: "border-orange-100",
      soft: "bg-orange-50 text-danger",
      dot: "bg-orange-600",
    },
  };
  const style = toneMap[priority.tone];
  const scoreLabel = priority.score >= 0 ? `+${priority.score} pontos` : `${priority.score} pontos`;

  return (
    <article className={`flex min-h-[360px] flex-col rounded-lg border ${style.border} bg-white p-5 shadow-soft`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-semibold ${style.soft}`}>
            <span className={`h-2.5 w-2.5 rounded-full ${style.dot}`} />
            {priority.criticality}
          </div>
          <h3 className="mt-4 text-xl font-semibold leading-tight text-ink">{priority.title}</h3>
        </div>
        <div className="rounded-lg bg-navy-950 px-3 py-2 text-right text-white">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-blue-100">Impacto SEO</p>
          <p className="mt-1 text-lg font-semibold">{scoreLabel}</p>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        <DecisionFact icon={Euro} label="Impacto financeiro" value={priority.financialImpact} />
        <DecisionFact icon={ShieldCheck} label="Impacto operacional" value={priority.operationalImpact} />
        <DecisionFact icon={Clock3} label="Tempo estimado" value={priority.resolutionTime} />
      </div>

      <div className="mt-5 rounded-lg bg-mist p-4">
        <p className="flex items-center gap-2 text-sm font-semibold text-ink">
          <Sparkles size={16} className="text-navy-700" aria-hidden="true" />
          Recomendação da IA
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-700">{priority.recommendation}</p>
      </div>

      <div className="mt-auto pt-5">
        <div className="mb-3 rounded-lg border border-line bg-white px-3 py-2 text-xs font-medium text-slate-600">
          Se não for resolvido: {priority.unresolvedPenalty} pontos no Índice SEO Core
        </div>
        <button
          className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-navy-900 px-4 text-sm font-semibold text-white hover:bg-navy-800"
          onClick={onAction}
          type="button"
        >
          <Target size={17} aria-hidden="true" />
          {priority.action}
        </button>
      </div>
    </article>
  );
}

function DailyDecisionCard({ action, onAction }: { action: DailyDecisionAction; onAction: () => void }) {
  const Icon = action.icon;
  const toneMap = {
    navy: {
      border: "border-blue-100",
      badge: "bg-blue-50 text-navy-800",
      icon: "bg-[#1d1d1f] text-white",
    },
    success: {
      border: "border-emerald-100",
      badge: "bg-emerald-50 text-success",
      icon: "bg-emerald-50 text-success",
    },
    warning: {
      border: "border-amber-100",
      badge: "bg-amber-50 text-warning",
      icon: "bg-amber-50 text-warning",
    },
    danger: {
      border: "border-orange-100",
      badge: "bg-orange-50 text-danger",
      icon: "bg-orange-50 text-danger",
    },
  };
  const style = toneMap[action.tone];

  return (
    <article className={`flex min-h-[320px] flex-col rounded-lg border ${style.border} bg-white p-5 shadow-soft`}>
      <div className="flex items-start justify-between gap-4">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg ${style.icon}`}>
          <Icon size={21} aria-hidden="true" />
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${style.badge}`}>
          {action.done ? "Controlado" : "Resolver hoje"}
        </span>
      </div>

      <h3 className="mt-5 text-xl font-semibold leading-tight text-ink">{action.title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{action.recommendation}</p>

      <div className="mt-5 grid gap-3">
        <DecisionFact icon={Euro} label={action.impactLabel} value={formatCurrency(action.impactValue)} />
        <DecisionFact icon={Clock3} label="Tempo para começar" value={action.timeToStart} />
        <DecisionFact icon={ShieldCheck} label="Motivo" value={action.reason} />
      </div>

      <button
        className={`mt-auto flex h-11 w-full items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold ${
          action.done ? "border border-line bg-white text-navy-800 hover:bg-mist" : "bg-navy-900 text-white hover:bg-navy-800"
        }`}
        onClick={onAction}
        type="button"
      >
        <Target size={17} aria-hidden="true" />
        {action.cta}
      </button>
    </article>
  );
}

function DecisionAnswer({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-black/10 bg-white p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#6e6e73]">{label}</p>
      <p className="mt-2 text-base font-semibold leading-snug text-[#1d1d1f]">{value}</p>
      <p className="mt-1 text-xs text-[#6e6e73]">{detail}</p>
    </div>
  );
}

function DecisionFact({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="flex gap-3 rounded-lg border border-line bg-white p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-mist text-navy-800">
        <Icon size={17} aria-hidden="true" />
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
        <p className="mt-1 text-sm font-medium leading-5 text-ink">{value}</p>
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-mist p-4">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}

function UploadBox({
  icon: Icon,
  title,
  detail,
}: {
  icon: LucideIcon;
  title: string;
  detail: string;
}) {
  return (
    <div className="flex min-h-24 items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-mist p-4 text-left">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white text-navy-800">
        <Icon size={19} aria-hidden="true" />
      </span>
      <span>
        <span className="block text-sm font-semibold text-ink">{title}</span>
        <span className="mt-1 block text-sm text-slate-600">{detail}</span>
      </span>
    </div>
  );
}

function DataTable({ columns, rows }: { columns: string[]; rows: string[][] }) {
  return (
    <div className="scrollbar-thin overflow-x-auto">
      <table className="w-full min-w-[620px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-mist">
            {columns.map((column) => (
              <th key={column} className="px-3 py-3 font-semibold text-slate-600">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.join("-")} className="border-b border-slate-100 last:border-0">
              {row.map((cell, index) => (
                <td key={`${cell}-${index}`} className="px-3 py-3 text-slate-700">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActionTable({
  columns,
  rows,
  onAction,
}: {
  columns: string[];
  rows: string[][];
  onAction: (rowIndex: number) => void;
}) {
  return (
    <div className="scrollbar-thin overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-line bg-mist">
            {columns.map((column) => (
              <th key={column} className="px-3 py-3 font-semibold text-slate-600">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={row.join("-")} className="border-b border-slate-100 last:border-0">
              {row.map((cell, index) => {
                const isAction = index === row.length - 1;
                return (
                  <td key={`${cell}-${index}`} className="px-3 py-3 text-slate-700">
                    {isAction && !["Resolvido", "Pago"].includes(cell) ? (
                      <button
                        className="rounded-lg border border-line px-3 py-1.5 text-xs font-semibold text-navy-800 hover:bg-mist"
                        onClick={() => onAction(rowIndex)}
                        type="button"
                      >
                        {cell}
                      </button>
                    ) : (
                      cell
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;
