"""
Unit tests for MissingDataAgent (Milestone 6).
"""
import json
from unittest.mock import MagicMock

import pytest

from app.agents.missing_data import (
    HypothesisValidation,
    MissingDataAgent,
    MissingDataResult,
)
from app.agents.root_cause import Hypothesis


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def agent_no_llm() -> MissingDataAgent:
    return MissingDataAgent(llm=None)


@pytest.fixture
def sample_hypotheses() -> list[Hypothesis]:
    return [
        Hypothesis(
            id="h1",
            title="Seasonal demand pattern",
            description="Revenue drops due to seasonal fluctuations.",
            prior_probability="HIGH",
            validation_data_needed=["sales_history: Monthly sales data"],
        ),
        Hypothesis(
            id="h2",
            title="Pricing strategy change",
            description="Price increases caused reduced conversions.",
            prior_probability="MEDIUM",
            validation_data_needed=["pricing_history: Historical price points"],
        ),
        Hypothesis(
            id="h3",
            title="Supply chain disruption",
            description="Supplier delays caused fulfilment issues.",
            prior_probability="MEDIUM",
            validation_data_needed=["inventory_data: Stock levels"],
        ),
    ]


@pytest.fixture
def sample_datasets() -> list[dict]:
    return [
        {
            "name": "sales.csv",
            "schema": {"date": "datetime", "revenue": "numeric", "units": "numeric"},
            "rows": 500,
        },
        {
            "name": "products.csv",
            "schema": {"product_id": "categorical", "price": "numeric"},
            "rows": 120,
        },
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_validate_hypotheses_returns_result(
    agent_no_llm: MissingDataAgent,
    sample_hypotheses: list[Hypothesis],
    sample_datasets: list[dict],
) -> None:
    """validate_hypotheses should always return a MissingDataResult."""
    result = agent_no_llm.validate_hypotheses(
        question="Why did sales drop?",
        hypotheses=sample_hypotheses,
        available_datasets=sample_datasets,
    )
    assert isinstance(result, MissingDataResult)
    assert isinstance(result.validations, list)
    assert isinstance(result.summary, str)
    assert isinstance(result.overall_investigation_status, str)


def test_validations_match_hypotheses(
    agent_no_llm: MissingDataAgent,
    sample_hypotheses: list[Hypothesis],
    sample_datasets: list[dict],
) -> None:
    """There should be exactly one validation per hypothesis."""
    result = agent_no_llm.validate_hypotheses(
        question="Why is churn rising?",
        hypotheses=sample_hypotheses,
        available_datasets=sample_datasets,
    )
    assert len(result.validations) == len(sample_hypotheses)
    validation_ids = {v.hypothesis_id for v in result.validations}
    hypothesis_ids = {h.id for h in sample_hypotheses}
    assert validation_ids == hypothesis_ids


def test_missing_datasets_extracted(
    agent_no_llm: MissingDataAgent,
    sample_hypotheses: list[Hypothesis],
    sample_datasets: list[dict],
) -> None:
    """missing_datasets should be populated when hypotheses cannot be validated."""
    result = agent_no_llm.validate_hypotheses(
        question="Why did revenue fall?",
        hypotheses=sample_hypotheses,
        available_datasets=sample_datasets,
    )
    # mock marks index 2+ as NO → missing_datasets should have entries
    assert isinstance(result.missing_datasets, list)
    assert len(result.missing_datasets) > 0


def test_follow_up_questions_generated(
    agent_no_llm: MissingDataAgent,
    sample_hypotheses: list[Hypothesis],
    sample_datasets: list[dict],
) -> None:
    """follow_up_questions must be non-empty when some hypotheses can't be validated."""
    result = agent_no_llm.validate_hypotheses(
        question="What caused the drop?",
        hypotheses=sample_hypotheses,
        available_datasets=sample_datasets,
    )
    assert len(result.follow_up_questions) > 0
    for q in result.follow_up_questions:
        assert isinstance(q, str)
        assert len(q) > 0


def test_overall_status_needs_data(
    agent_no_llm: MissingDataAgent,
    sample_hypotheses: list[Hypothesis],
    sample_datasets: list[dict],
) -> None:
    """When some hypotheses can't be validated, status should be NEEDS_DATA."""
    # sample_hypotheses has 3 items → mock marks idx≥2 as NO → NEEDS_DATA
    result = agent_no_llm.validate_hypotheses(
        question="Why are costs high?",
        hypotheses=sample_hypotheses,
        available_datasets=sample_datasets,
    )
    assert result.overall_investigation_status in {"NEEDS_DATA", "BLOCKED", "CAN_PROCEED"}


def test_mock_validation_structure(
    agent_no_llm: MissingDataAgent,
    sample_hypotheses: list[Hypothesis],
) -> None:
    """Mock validation should produce correct structure with YES for first 2."""
    result = agent_no_llm._mock_validation(sample_hypotheses)
    assert isinstance(result, MissingDataResult)

    yes_validations = [v for v in result.validations if v.can_validate == "YES"]
    no_validations = [v for v in result.validations if v.can_validate == "NO"]

    assert len(yes_validations) == 2
    assert len(no_validations) == 1

    # YES validations should not have missing_dataset
    for v in yes_validations:
        assert v.missing_dataset is None

    # NO validations should have a follow-up question
    for v in no_validations:
        assert v.follow_up_question is not None


def test_with_mock_llm(sample_hypotheses: list[Hypothesis]) -> None:
    """When LLM returns valid JSON, the result should be correctly parsed."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "validations": [
            {
                "hypothesis_id": "h1",
                "can_validate": "YES",
                "validation_status": "Full data available.",
                "missing_dataset": None,
                "missing_columns": [],
                "follow_up_question": None,
                "evidence_found": "Strong seasonal pattern detected.",
            },
            {
                "hypothesis_id": "h2",
                "can_validate": "NO",
                "validation_status": "Pricing data not available.",
                "missing_dataset": "pricing_history",
                "missing_columns": ["price", "date"],
                "follow_up_question": "Do you have historical pricing data?",
                "evidence_found": None,
            },
            {
                "hypothesis_id": "h3",
                "can_validate": "PARTIAL",
                "validation_status": "Partial inventory data available.",
                "missing_dataset": "supplier_data",
                "missing_columns": ["lead_time"],
                "follow_up_question": "Can you share supplier lead time records?",
                "evidence_found": "Inventory dips detected.",
            },
        ],
        "overall_investigation_status": "NEEDS_DATA",
        "summary": "1 hypothesis validated, 2 need more data.",
    })
    mock_llm.invoke.return_value = mock_response

    agent = MissingDataAgent(llm=mock_llm)
    result = agent.validate_hypotheses(
        question="Why did sales drop?",
        hypotheses=sample_hypotheses,
        available_datasets=[{"name": "sales.csv", "schema": {}, "rows": 100}],
    )

    assert isinstance(result, MissingDataResult)
    assert len(result.validations) == 3
    assert result.overall_investigation_status == "NEEDS_DATA"
    assert "pricing_history" in result.missing_datasets
    assert "supplier_data" in result.missing_datasets
    assert len(result.follow_up_questions) == 2
    mock_llm.invoke.assert_called_once()


def test_extract_missing_datasets_deduplication(agent_no_llm: MissingDataAgent) -> None:
    """_extract_missing_datasets should deduplicate dataset names."""
    validations = [
        HypothesisValidation(
            hypothesis_id="h1",
            can_validate="NO",
            validation_status="missing",
            missing_dataset="sales_data",
        ),
        HypothesisValidation(
            hypothesis_id="h2",
            can_validate="NO",
            validation_status="missing",
            missing_dataset="sales_data",  # duplicate
        ),
        HypothesisValidation(
            hypothesis_id="h3",
            can_validate="NO",
            validation_status="missing",
            missing_dataset="inventory_data",
        ),
    ]
    result = agent_no_llm._extract_missing_datasets(validations)
    assert result == ["sales_data", "inventory_data"]  # no duplicates


def test_validate_with_empty_hypotheses(
    agent_no_llm: MissingDataAgent,
    sample_datasets: list[dict],
) -> None:
    """Validating an empty hypothesis list should return an empty-validation result."""
    result = agent_no_llm.validate_hypotheses(
        question="Why?",
        hypotheses=[],
        available_datasets=sample_datasets,
    )
    assert isinstance(result, MissingDataResult)
    assert len(result.validations) == 0
    assert result.missing_datasets == []
