from __future__ import annotations

from typing import Iterable, Mapping

BILLING_CONTRACT_VERSION = "2026-08-20"
BILLING_REQUIRED_SHEETS = (
    "Faturação Separada",
    "Resumo Vendedores",
    "Mapa Diário",
)

BILLING_AGENT_CONTRACT = {
    "id": "svp_auto_billing_daily_v1",
    "version": BILLING_CONTRACT_VERSION,
    "output": {
        "type": "xlsx",
        "single_workbook": True,
        "required_sheets": list(BILLING_REQUIRED_SHEETS),
        "completion_policy": "all_required_or_failed",
        "chat_only_result_allowed": False,
    },
    "faturacao_separada": {
        "locations": ["Coimbra", "Picoto"],
        "series": ["CUSA", "CNOV", "PUSA", "PNOV", "POFI"],
        "document_types": ["FR", "FT", "NC"],
        "remove_document_types": ["GT", "PF"],
        "remove_cancelled_documents": True,
        "credit_notes_negative": True,
        "credit_note_states": ["Liquidado", "Pendente"],
        "required_columns": [
            "ID",
            "Documento",
            "Data Doc.",
            "Entidade",
            "Total",
            "Total liquido",
            "Total IVA",
            "Estado",
            "Doc. Fornecedor",
            "Nº Enc. / Req. Ext.",
            "Canal de Anúncios",
            "Vendedor",
            "Forma de Liquidação",
        ],
        "required_totals": ["Total Coimbra", "Total Picoto", "Total Geral"],
    },
    "resumo_vendedores": {
        "value_basis": "Total líquido",
        "group_by": ["local", "vendedor", "tipo_documento", "serie"],
        "fr_separate_from_ft": True,
        "credit_note_states": ["Liquidado", "Pendente"],
        "required_locations": ["Coimbra", "Picoto"],
        "requires_subtotals": True,
    },
    "mapa_diario": {
        "locations": ["Coimbra", "Picoto"],
        "vehicle_groups": ["Usado", "Novo"],
        "pofi_separate": True,
        "columns": [
            "FR c/ IVA",
            "FR s/ IVA",
            "FT c/ IVA",
            "FT s/ IVA",
            "NC c/ IVA",
            "NC s/ IVA",
            "TOTAL c/ IVA",
            "TOTAL s/ IVA",
        ],
        "total_formula": "FR + FT + NC",
        "required_totals": [
            "TOTAL COIMBRA — USADO + NOVO",
            "TOTAL PICOTO — USADO + NOVO",
            "TOTAL PICOTO GERAL — USADO + NOVO + POFI",
            "TOTAL GERAL SVP AUTO",
        ],
        "credit_note_detail_by_state": True,
        "sucatas_separate": True,
        "salvados_separate": True,
        "keep_zero_sections": True,
    },
    "audit": {
        "required": True,
        "checks": [
            "three_required_sheets_present",
            "coimbra_picoto_separation",
            "novo_usado_separation",
            "sucatas_salvados_separation",
            "fr_ft_separation",
            "nc_negative",
            "nc_liquidado_pendente",
            "seller_summary_uses_net_total",
            "daily_map_total_is_fr_plus_ft_plus_nc",
            "workbook_totals_reconciled",
        ],
    },
}


def validate_billing_delivery(
    sheet_names: Iterable[str],
    checks: Mapping[str, bool] | None = None,
) -> dict:
    """Validate whether a billing task is allowed to finish as COMPLETED.

    The workbook generator/auditor reports its checks here. Missing required
    sheets or any failed/missing audit check force the task to FAILED.
    """

    actual = {str(name).strip() for name in sheet_names}
    missing_sheets = [name for name in BILLING_REQUIRED_SHEETS if name not in actual]
    supplied_checks = dict(checks or {})
    required_checks = BILLING_AGENT_CONTRACT["audit"]["checks"]
    failed_checks = [name for name in required_checks if supplied_checks.get(name) is not True]
    valid = not missing_sheets and not failed_checks

    return {
        "contract_id": BILLING_AGENT_CONTRACT["id"],
        "contract_version": BILLING_CONTRACT_VERSION,
        "status": "COMPLETED" if valid else "FAILED",
        "valid": valid,
        "required_output": "xlsx",
        "required_sheets": list(BILLING_REQUIRED_SHEETS),
        "missing_sheets": missing_sheets,
        "failed_checks": failed_checks,
        "completion_policy": "all_required_or_failed",
    }
