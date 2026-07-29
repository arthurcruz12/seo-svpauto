STRATEGY_NORTH_STAR = (
    "O SEO e o copiloto financeiro-operacional das PME: liga dados dispersos, "
    "encontra perdas escondidas e transforma operacoes diarias em decisoes de lucro."
)

STRATEGY_PILLARS = [
    {
        "id": "financialImpact",
        "title": "Dor economica recorrente",
        "question": "Reduz perda, recupera margem ou acelera cobranca todos os meses?",
        "outcome": "O cliente ve dinheiro protegido ou recuperado.",
    },
    {
        "id": "recurringPain",
        "title": "Mercado expansivel",
        "question": "A dor existe em muitas PME com inventario, canais, fornecedores ou contabilidade operacional?",
        "outcome": "O produto pode sair do nicho inicial e escalar.",
    },
    {
        "id": "proprietaryData",
        "title": "Dados proprios",
        "question": "Cria historico de vendas, inventario, margem, risco, pagamentos ou decisoes?",
        "outcome": "O SEO aprende com dados que concorrentes nao possuem.",
    },
    {
        "id": "decisionAutomation",
        "title": "Automacao de decisao",
        "question": "Diz o que comprar, vender, cobrar, negociar ou corrigir?",
        "outcome": "O produto deixa de mostrar numeros e passa a orientar acao.",
    },
    {
        "id": "securityTrust",
        "title": "Seguranca e confianca",
        "question": "Respeita autenticacao, permissoes, auditoria, backups, RGPD e isolamento por empresa?",
        "outcome": "Empresas confiam dados sensiveis ao produto.",
    },
]

STRATEGY_PROCESS = [
    {
        "title": "Definir a dor economica",
        "action": "Escrever que perda mensal a funcionalidade combate.",
        "evidence": "Stock parado, margem baixa, cobranca atrasada ou erro de conciliacao.",
    },
    {
        "title": "Definir a decisao recomendada",
        "action": "Converter o insight numa acao objetiva para o cliente.",
        "evidence": "Cobrar cliente, baixar preco, nao recomprar SKU ou rever canal.",
    },
    {
        "title": "Guardar historico",
        "action": "Persistir dado, decisao, utilizador, data, resultado e impacto estimado.",
        "evidence": "O historico alimenta comparacoes e IA proprietaria.",
    },
    {
        "title": "Medir antes e depois",
        "action": "Comparar diario, semanal, mensal, trimestral e anual quando fizer sentido.",
        "evidence": "Capital em risco, margem, stock parado, saldos e pendencias.",
    },
    {
        "title": "Aplicar seguranca desde o inicio",
        "action": "Garantir permissao, auditoria, segregacao por empresa e preparacao para backup.",
        "evidence": "Confianca e funcionalidade de produto.",
    },
]

SAAS_PLANS = [
    {"plan": "Starter", "customer": "PME pequena", "value": "Importacao, dashboard, relatorio e historico basico."},
    {
        "plan": "Professional",
        "customer": "Empresa com inventario e financeiro",
        "value": "IA, snapshots, cobranca, conciliacao e decisoes priorizadas.",
    },
    {
        "plan": "Business",
        "customer": "Operacao multiempresa ou mais complexa",
        "value": "Integracoes, auditoria, permissoes e automacoes.",
    },
    {"plan": "Enterprise", "customer": "Parceiros, grupos e consultoras", "value": "API, compliance, suporte e SLA."},
]


def strategy_operating_model() -> dict:
    return {
        "northStar": STRATEGY_NORTH_STAR,
        "pillars": STRATEGY_PILLARS,
        "process": STRATEGY_PROCESS,
        "saasPlans": SAAS_PLANS,
        "rule": "Construir apenas funcionalidades que geram decisao de lucro, historico proprietario ou confianca SaaS.",
    }


def score_strategy_fit(signals: list[str]) -> dict:
    pillar_ids = {pillar["id"] for pillar in STRATEGY_PILLARS}
    active = set(signals).intersection(pillar_ids)
    score = round((len(active) / len(pillar_ids)) * 100)
    missing = [pillar["title"] for pillar in STRATEGY_PILLARS if pillar["id"] not in active]
    if score >= 70:
        decision = "Construir agora"
    elif score >= 45:
        decision = "Refinar antes de construir"
    else:
        decision = "Nao priorizar"
    return {"score": score, "decision": decision, "missing": missing}
