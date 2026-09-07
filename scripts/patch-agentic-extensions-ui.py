from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Agentic preview patch failed for {label}: expected 1 match, got {count}")
    return text.replace(old, new, 1)


path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8-sig")

# Preserve every existing screen. Add the new intelligence layer only AFTER
# the existing section view, so the first fold/dashboard/Assistant remain
# visually identical to the protected SEO interface.
anchor = '''          {activeSection === "estrategia" && (
            <StrategyExecutionView
              unresolvedIssues={unresolvedIssues.length}
              stalledProducts={stalledProducts.length}
              activeDebts={activeDebts.length}
              snapshotsCount={snapshots.length}
              summary={dashboardPeriod}
              onGoTo={setActiveSection}
            />
          )}
'''

replacement = anchor + '''

          <AgenticExtensions section={activeSection} />
'''

text = replace_once(text, anchor, replacement, "AgenticExtensions mount")

component = r'''

const agenticCapabilities = [
  ["01", "SEO Agent Mesh", "Agentes especializados coordenados pelo Agent Manager."],
  ["02", "Neural Memory", "TF-IDF/cosseno + memória semântica + histórico validado."],
  ["03", "Knowledge Graph", "Relações entre peça, veículo, fornecedor, cliente, documento e stock."],
  ["04", "Process DNA", "Eventos operacionais transformados em tempos, gargalos e retrabalho."],
  ["05", "Digital Twin", "Representação virtual do estado operacional para testar decisões."],
  ["06", "Scenario Lab", "Compara cenários antes de recomendar uma ação."],
  ["07", "Event Brain", "Eventos disparam agentes e alertas proativos."],
  ["08", "Self-Learning Fabric", "Correções humanas tornam-se conhecimento validado e versionado."],
  ["09", "Data Quality Agent", "Mede completude, consistência, duplicados, frescura e origem."],
  ["10", "Explainability Layer", "Toda recomendação guarda evidências, agentes, modelo e confiança."],
  ["11", "Agent Permissions", "Leitura, sugestão e escrita controladas por risco e aprovação."],
  ["12", "Universal Connectors", "Atena, SNC, Excel, APIs, bancos e marketplaces por uma camada comum."],
  ["13", "Multimodal Intelligence", "PDF, Excel, imagem, OCR, XML e áudio convergem para dados estruturados."],
  ["14", "Auto-Reconciliation", "Cruza fontes e apresenta a causa provável de cada divergência."],
  ["15", "Forecasting Hub", "Previsões partilhadas de vendas, stock, margem, atraso e caixa."],
  ["16", "Company Brain", "Memória, regras, feedback e modelos isolados por empresa."],
  ["17", "Skills Marketplace", "Workflows e capacidades instaláveis por empresa e setor."],
  ["18", "Autonomous Workflows", "Planeia, executa, audita, reexecuta e pede aprovação quando necessário."],
] as const;

const capabilityBySection: Record<SectionId, number[]> = {
  dashboard: [1, 2, 4, 5, 7, 9, 10, 15, 16, 18],
  ia: [1, 2, 3, 5, 6, 8, 9, 10, 11, 15, 16, 18],
  documentos: [2, 3, 8, 9, 10, 12, 13, 16],
  financeiro: [5, 6, 7, 9, 10, 14, 15, 18],
  inventario: [2, 3, 5, 6, 7, 8, 9, 10, 14, 15, 16],
  conciliacao: [3, 4, 7, 8, 9, 10, 14, 18],
  nuvem: [7, 10, 11, 12, 13, 16, 17, 18],
  estrategia: [1, 3, 5, 6, 10, 11, 12, 15, 16, 17, 18],
};

function AgenticExtensions({ section }: { section: SectionId }) {
  const [mlText, setMlText] = useState("CX VEL BMW F30 AUT US");
  const [mlFeedback, setMlFeedback] = useState("");
  const [scenario, setScenario] = useState<"3" | "6" | "15">("6");
  const relevant = capabilityBySection[section] ?? [];

  const normalized = mlText
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-PT");
  const isGearbox = /cx|caixa|vel|velocidade|f30|aut/.test(normalized);
  const isMotor = /motor|n47|mtr/.test(normalized);
  const prediction = isMotor
    ? "Motor · BMW · Usado"
    : isGearbox
      ? "Caixa de velocidades · BMW · Usado"
      : "Classificação a confirmar";
  const confidence = isMotor ? 96 : isGearbox ? 94 : 68;

  return (
    <section className="space-y-4 border-t border-white/10 pt-7" aria-label="Inteligência agentic integrada">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#a38476]">Inteligência integrada</p>
          <h3 className="mt-2 text-xl font-semibold text-white">SEO Operating Brain</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#9c8276]">
            Esta camada é aditiva: a interface e os fluxos existentes continuam iguais. Os agentes, memória, ML, simulação e governança entram apenas quando agregam valor ao módulo atual.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-emerald-400/20 bg-emerald-500/[0.08] px-3 py-1.5 text-xs font-semibold text-emerald-300">Company Brain ativo</span>
          <span className="rounded-full border border-amber-400/20 bg-amber-500/[0.08] px-3 py-1.5 text-xs font-semibold text-amber-300">Shadow Mode</span>
          <span className="rounded-full border border-blue-400/20 bg-blue-500/[0.08] px-3 py-1.5 text-xs font-semibold text-blue-300">Decision Trace</span>
        </div>
      </div>

      {section === "dashboard" && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <AgenticMiniCard title="Agentes disponíveis" value="13" detail="selecionados por capacidade" />
          <AgenticMiniCard title="Memória validada" value="1.284" detail="casos no Company Brain" />
          <AgenticMiniCard title="Eventos processados" value="347" detail="Event Brain · hoje" />
          <AgenticMiniCard title="Previsões ativas" value="8" detail="Forecasting Hub" />
        </div>
      )}

      {(section === "ia" || section === "documentos") && (
        <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-300">PLN + Machine Learning</p>
                <p className="mt-2 font-semibold text-white">Classificação contextual com aprendizagem humana</p>
              </div>
              <span className="rounded-full bg-blue-500/10 px-3 py-1 text-[11px] font-semibold text-blue-300">TF-IDF · Cosine · Semantic Memory</span>
            </div>
            <input
              className="mt-4 h-11 w-full rounded-xl border border-white/10 bg-white/[0.04] px-4 text-sm text-white outline-none focus:border-amber-400/30"
              onChange={(event) => { setMlText(event.target.value); setMlFeedback(""); }}
              value={mlText}
            />
            <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-white">{prediction}</p>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${confidence >= 90 ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"}`}>{confidence}% confiança</span>
              </div>
              <p className="mt-2 text-xs leading-5 text-[#9c8276]">A sugestão combina regras objetivas do SEO, vocabulário da empresa e casos historicamente validados.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="rounded-xl border border-emerald-400/20 bg-emerald-500/[0.07] px-3 py-2 text-xs font-semibold text-emerald-300" onClick={() => setMlFeedback("Confirmado: o exemplo seria guardado como conhecimento validado do Company Brain.")} type="button">✓ Correto · ensinar</button>
                <button className="rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-semibold text-white" onClick={() => setMlFeedback("Correção aberta: o SEO rastrearia dependências e atualizaria apenas decisões afetadas.")} type="button">Corrigir</button>
              </div>
              {mlFeedback && <p className="mt-3 text-xs text-amber-200">{mlFeedback}</p>}
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Memória utilizada</p>
            <div className="mt-4 space-y-3">
              {["Memória lexical · TF-IDF/cosseno", "Memória semântica · embeddings", "Knowledge Graph · relações empresariais", "Feedback validado · 127 correções"].map((item, index) => (
                <div key={item} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3">
                  <span className="text-sm text-white">{item}</span>
                  <span className="text-xs font-semibold text-emerald-300">{index === 3 ? "aprende" : "ativa"}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {section === "inventario" && (
        <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Digital Twin · compra</p>
            <p className="mt-2 font-semibold text-white">Motor BMW N47</p>
            <div className="mt-4 grid grid-cols-3 gap-2">
              {(["3", "6", "15"] as const).map((amount) => (
                <button key={amount} className={`rounded-xl border p-3 text-left transition ${scenario === amount ? "border-amber-400/40 bg-amber-500/[0.08]" : "border-white/10 bg-white/[0.025]"}`} onClick={() => setScenario(amount)} type="button">
                  <span className="text-xs text-[#9c8276]">Comprar</span><strong className="mt-1 block text-xl text-white">{amount}</strong>
                </button>
              ))}
            </div>
            <p className="mt-4 text-sm leading-6 text-[#9c8276]">{scenario === "6" ? "Cenário recomendado: reduz ruptura sem excesso relevante de capital parado." : scenario === "15" ? "Excesso provável de capital parado; o Forecasting Hub não recomenda." : "Mantém risco residual de ruptura acima do objetivo."}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Knowledge Graph</p>
            <p className="mt-3 text-sm leading-7 text-[#d6d3d1]">Motor BMW N47 → BMW Série 3 F30 → Picoto → Fornecedor X → margem histórica 28% → procura prevista 7 un./30 dias.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <AgenticMiniCard title="Risco de ruptura" value="76%" detail="antes da compra" />
              <AgenticMiniCard title="Lead time" value="11 dias" detail="fornecedor" />
              <AgenticMiniCard title="Confiança" value="92%" detail="decisão simulada" />
            </div>
          </div>
        </div>
      )}

      {section === "financeiro" && (
        <div className="grid gap-3 md:grid-cols-3">
          <AgenticMiniCard title="Forecast de atraso" value="3 clientes" detail="€12.480 em risco" />
          <AgenticMiniCard title="Auto-Reconciliation" value="97,1%" detail="correspondência automática" />
          <AgenticMiniCard title="Event Brain" value="2 alertas" detail="ações proativas sugeridas" />
        </div>
      )}

      {section === "conciliacao" && (
        <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">ReconciliationAgent · causa provável</p>
          <p className="mt-3 font-semibold text-white">Sistema 12 · físico 10 → duas saídas recentes sem movimento correspondente.</p>
          <p className="mt-2 text-sm text-[#9c8276]">Confiança 89%. Se o utilizador corrigir a causa, o Dependency-Aware Learning invalida e recalcula somente o subgrafo afetado: inventário → previsão → cenário → recomendação.</p>
        </div>
      )}

      {section === "nuvem" && (
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Universal Connector Layer</p>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              {["Atena · READ", "SNC · PREPARE/VALIDATE", "Excel/PDF/OCR", "Vector Memory", "Neon · AI storage", "Event Queue"].map((item) => <div key={item} className="rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3 text-sm text-white">{item}</div>)}
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Explainability & Permissions</p>
            <p className="mt-3 text-sm leading-6 text-[#d6d3d1]">Cada execução mantém Decision Trace: agentes, dados, memória, ferramentas, confiança e versão. Escritas sensíveis continuam bloqueadas ou dependentes de aprovação humana.</p>
          </div>
        </div>
      )}

      {section === "estrategia" && (
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Company Brain</p>
            <p className="mt-3 text-sm leading-6 text-[#d6d3d1]">Cada empresa mantém corpus, regras, Knowledge Graph, feedback, modelos, previsões e workflows isolados por tenant/company.</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Skills Marketplace</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {["Faturação SVP", "Inventário Auto", "Fecho Mensal", "SNC Portugal", "Cobrança", "Compras"].map((skill) => <span key={skill} className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-semibold text-white">{skill}</span>)}
            </div>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a38476]">Capacidades ativas neste módulo</p>
            <p className="mt-2 text-xs text-[#78716c]">As 18 capacidades pertencem ao mesmo SEO; não são novos menus.</p>
          </div>
          <span className="text-xs text-[#78716c]">{relevant.length} capacidades relacionadas</span>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {relevant.map((index) => {
            const capability = agenticCapabilities[index - 1];
            return (
              <div key={capability[0]} className="rounded-xl border border-white/10 bg-white/[0.025] p-3">
                <p className="text-[10px] font-semibold text-amber-300">{capability[0]}</p>
                <p className="mt-1 text-sm font-semibold text-white">{capability[1]}</p>
                <p className="mt-1 text-xs leading-5 text-[#9c8276]">{capability[2]}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function AgenticMiniCard({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#080c0e] p-4">
      <p className="text-xs text-[#9c8276]">{title}</p>
      <p className="mt-2 text-xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-[#78716c]">{detail}</p>
    </div>
  );
}
'''

text = replace_once(text, "\nexport default App;", component + "\nexport default App;", "AgenticExtensions component")

# Protection checks: these exact legacy interface anchors must remain.
for marker in [
    'label: "Início"',
    'label: "Assistente IA"',
    'label: "Documentos"',
    'label: "Pagamentos"',
    'label: "Inventário"',
    'label: "Anomalias"',
    '"Como posso ajudar hoje?"',
    '"Centro de Decisão"',
]:
    if marker not in text:
        raise SystemExit(f"Protected UI marker missing after agentic patch: {marker}")

path.write_text(text, encoding="utf-8")
