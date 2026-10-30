"""
Unit tests for RootCauseAgent (Milestone 5).
"""
import json
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.agents.root_cause import (
    Hypothesis,
    RootCauseAgent,
    RootCauseResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def agent_no_llm() -> RootCauseAgent:
    """RootCauseAgent with no LLM — uses mock hypotheses."""
    return RootCauseAgent(llm=None)


@pytest.fixture
def sample_datasets() -> list[dict]:
    return [
        {"name": "sales.csv", "schema": {"date": "datetime", "revenue": "numeric"}, "rows": 500},
        {"name": "products.csv", "schema": {"product_id": "categorical", "price": "numeric"}, "rows": 120},
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_generate_hypotheses_returns_result(agent_no_llm: RootCauseAgent) -> None:
    """generate_hypotheses should return a RootCauseResult regardless of LLM availability."""
    result = agent_no_llm.generate_hypotheses(
        question="Why did sales drop last quarter?",
        dataset_context="Dataset: sales.csv\n  Rows: 1000\n  Columns: date, revenue",
    )
    assert isinstance(result, RootCauseResult)
    assert result.question == "Why did sales drop last quarter?"
    assert isinstance(result.generated_at, datetime)
    assert len(result.hypotheses) > 0


def test_hypotheses_have_required_fields(agent_no_llm: RootCauseAgent) -> None:
    """Each Hypothesis must contain id, title, description, prior_probability."""
    result = agent_no_llm.generate_hypotheses(
        question="Why is customer churn increasing?",
        dataset_context="Dataset: customers.csv\n  Rows: 200\n  Columns: customer_id, churn",
    )
    for hyp in result.hypotheses:
        assert isinstance(hyp, Hypothesis)
        assert hyp.id, "Hypothesis must have a non-empty id"
        assert hyp.title, "Hypothesis must have a non-empty title"
        assert hyp.description, "Hypothesis must have a non-empty description"
        assert hyp.prior_probability in {"LOW", "MEDIUM", "HIGH"}


def test_mock_hypotheses_returns_five(agent_no_llm: RootCauseAgent) -> None:
    """When no LLM is configured, exactly 5 mock hypotheses should be returned."""
    result = agent_no_llm.generate_hypotheses(
        question="Why is revenue declining?",
        dataset_context="No datasets available.",
    )
    assert len(result.hypotheses) == 5


def test_hypotheses_prior_probability_valid(agent_no_llm: RootCauseAgent) -> None:
    """prior_probability for every hypothesis must be one of LOW/MEDIUM/HIGH."""
    result = agent_no_llm.generate_hypotheses(
        question="Why are profits falling?",
        dataset_context="Dataset: profits.csv\n  Rows: 300\n  Columns: month, profit",
    )
    valid_values = {"LOW", "MEDIUM", "HIGH"}
    for hyp in result.hypotheses:
        assert hyp.prior_probability in valid_values, (
            f"Hypothesis {hyp.id!r} has invalid prior_probability: {hyp.prior_probability!r}"
        )


def test_build_dataset_context(agent_no_llm: RootCauseAgent, sample_datasets: list[dict]) -> None:
    """_build_dataset_context should produce a string containing all dataset names."""
    context = agent_no_llm._build_dataset_context(sample_datasets)
    assert isinstance(context, str)
    assert "sales.csv" in context
    assert "products.csv" in context


def test_build_dataset_context_empty(agent_no_llm: RootCauseAgent) -> None:
    """_build_dataset_context with empty list should return a sensible fallback string."""
    context = agent_no_llm._build_dataset_context([])
    assert "No datasets" in context


def test_generate_hypotheses_with_mock_llm() -> None:
    """With a mocked LLM returning valid JSON, hypotheses should be parsed correctly."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "hypotheses": [
            {
                "id": "h1",
                "title": "Test Hypothesis",
                "description": "A test description of the hypothesis.",
                "prior_probability": "HIGH",
                "validation_data_needed": ["test_data: some description"],
            },
            {
                "id": "h2",
                "title": "Another Hypothesis",
                "description": "Second hypothesis description.",
                "prior_probability": "LOW",
                "validation_data_needed": ["other_data: another description"],
            },
        ]
    })
    mock_llm.invoke.return_value = mock_response

    agent = RootCauseAgent(llm=mock_llm)
    result = agent.generate_hypotheses(
        question="Why are costs rising?",
        dataset_context="Dataset: costs.csv\n  Rows: 400\n  Columns: month, cost",
    )

    assert isinstance(result, RootCauseResult)
    assert len(result.hypotheses) == 2
    assert result.hypotheses[0].id == "h1"
    assert result.hypotheses[0].title == "Test Hypothesis"
    assert result.hypotheses[0].prior_probability == "HIGH"
    assert result.hypotheses[1].prior_probability == "LOW"
    mock_llm.invoke.assert_called_once()


def test_hypothesis_default_fields() -> None:
    """Hypothesis defaults: is_validated=False, evidence=None, confidence_score=None."""
    hyp = Hypothesis(
        id="h1",
        title="Test",
        description="Test description",
        prior_probability="MEDIUM",
        validation_data_needed=[],
    )
    assert hyp.is_validated is False
    assert hyp.evidence is None
    assert hyp.confidence_score is None


def test_llm_failure_falls_back_to_mock() -> None:
    """When the LLM raises an exception, the agent should return mock hypotheses."""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = RuntimeError("LLM unavailable")

    agent = RootCauseAgent(llm=mock_llm)
    result = agent.generate_hypotheses(
        question="Why did orders drop?",
        dataset_context="Dataset: orders.csv",
    )

    assert isinstance(result, RootCauseResult)
    assert len(result.hypotheses) == 5  # fallback mock
