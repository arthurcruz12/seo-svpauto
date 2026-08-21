from app.billing_contract import BILLING_AGENT_CONTRACT, BILLING_REQUIRED_SHEETS, validate_billing_delivery


def _all_checks_passed():
    return {name: True for name in BILLING_AGENT_CONTRACT["audit"]["checks"]}


def test_billing_contract_requires_exact_three_core_sheets():
    assert BILLING_REQUIRED_SHEETS == (
        "Faturação Separada",
        "Resumo Vendedores",
        "Mapa Diário",
    )
    assert BILLING_AGENT_CONTRACT["output"]["single_workbook"] is True
    assert BILLING_AGENT_CONTRACT["output"]["chat_only_result_allowed"] is False
    assert BILLING_AGENT_CONTRACT["output"]["completion_policy"] == "all_required_or_failed"


def test_billing_delivery_is_completed_only_when_all_sheets_and_checks_pass():
    result = validate_billing_delivery(BILLING_REQUIRED_SHEETS, _all_checks_passed())

    assert result["valid"] is True
    assert result["status"] == "COMPLETED"
    assert result["missing_sheets"] == []
    assert result["failed_checks"] == []


def test_billing_delivery_fails_if_any_required_sheet_is_missing():
    result = validate_billing_delivery(
        ["Faturação Separada", "Resumo Vendedores"],
        _all_checks_passed(),
    )

    assert result["valid"] is False
    assert result["status"] == "FAILED"
    assert result["missing_sheets"] == ["Mapa Diário"]


def test_billing_delivery_fails_if_any_audit_rule_fails():
    checks = _all_checks_passed()
    checks["nc_liquidado_pendente"] = False

    result = validate_billing_delivery(BILLING_REQUIRED_SHEETS, checks)

    assert result["valid"] is False
    assert result["status"] == "FAILED"
    assert "nc_liquidado_pendente" in result["failed_checks"]


def test_contract_encodes_reference_workbook_rules_without_company_data():
    separated = BILLING_AGENT_CONTRACT["faturacao_separada"]
    sellers = BILLING_AGENT_CONTRACT["resumo_vendedores"]
    daily = BILLING_AGENT_CONTRACT["mapa_diario"]

    assert separated["series"] == ["CUSA", "CNOV", "PUSA", "PNOV", "POFI"]
    assert separated["credit_notes_negative"] is True
    assert separated["credit_note_states"] == ["Liquidado", "Pendente"]
    assert sellers["value_basis"] == "Total líquido"
    assert sellers["fr_separate_from_ft"] is True
    assert daily["total_formula"] == "FR + FT + NC"
    assert daily["sucatas_separate"] is True
    assert daily["salvados_separate"] is True
    assert daily["keep_zero_sections"] is True
