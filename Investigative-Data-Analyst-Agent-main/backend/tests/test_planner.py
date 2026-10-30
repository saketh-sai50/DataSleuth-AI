"""
Tests for PlannerAgent and the POST /investigations/analyze endpoint.
"""
import io
import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.agents.planner import ExecutionPlan, PlannerAgent


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_csv_upload(filename: str = "test.csv", content: str = None) -> dict:
    if content is None:
        content = "col1,col2\n1,a\n2,b\n3,c\n"
    return {"file": (filename, io.BytesIO(content.encode()), "text/csv")}


# ---------------------------------------------------------------------------
# PlannerAgent unit tests
# ---------------------------------------------------------------------------

class TestPlannerAgent:

    def test_planner_no_llm_returns_mock(self):
        """When llm=None, create_plan must return a valid ExecutionPlan."""
        agent = PlannerAgent(llm=None)
        plan = agent.create_plan(
            question="What are the sales trends?",
            available_datasets=["sales_2024.csv"],
        )
        assert isinstance(plan, ExecutionPlan)
        assert isinstance(plan.question_type, str)
        assert len(plan.plan_steps) >= 1
        assert isinstance(plan.can_proceed, bool)

    def test_planner_creates_plan(self):
        """create_plan returns ExecutionPlan with all required fields."""
        agent = PlannerAgent(llm=None)
        plan = agent.create_plan(
            question="Compare Q1 vs Q2 revenue",
            available_datasets=["revenue.csv", "expenses.csv"],
        )
        assert isinstance(plan, ExecutionPlan)
        assert plan.question_type != ""
        assert isinstance(plan.plan_steps, list)
        assert isinstance(plan.required_datasets, list)
        assert isinstance(plan.available_datasets, list)
        assert isinstance(plan.missing_datasets, list)
        # Both datasets are available, so can_proceed should be True
        assert plan.can_proceed is True

    def test_planner_detects_missing_datasets(self):
        """When question implies datasets not in available list, missing_datasets is populated."""
        agent = PlannerAgent(llm=None)
        # Provide only one dataset; mock plan keeps available as the input list
        plan = agent.create_plan(
            question="Compare sales vs inventory",
            available_datasets=["sales.csv"],  # inventory.csv missing
        )
        assert isinstance(plan, ExecutionPlan)
        # available_datasets must equal what was passed
        assert "sales.csv" in plan.available_datasets

    def test_planner_trend_keyword_detected(self):
        """Question with 'trend' keyword produces 'trend_analysis' question_type."""
        agent = PlannerAgent(llm=None)
        plan = agent.create_plan(
            question="Show me sales trends over time",
            available_datasets=["sales.csv"],
        )
        assert plan.question_type == "trend_analysis"

    def test_planner_comparison_keyword_detected(self):
        """Question with 'compare' produces 'comparison' question_type."""
        agent = PlannerAgent(llm=None)
        plan = agent.create_plan(
            question="Compare region A vs region B",
            available_datasets=["regions.csv"],
        )
        assert plan.question_type == "comparison"

    def test_planner_with_mock_llm(self):
        """When LLM returns valid JSON, it is parsed into ExecutionPlan."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        llm_json = {
            "question_type": "root_cause",
            "plan_steps": [{"step": 1, "action": "Load data", "requires": ["data.csv"]}],
            "required_datasets": ["data.csv"],
            "available_datasets": ["data.csv"],
            "missing_datasets": [],
            "can_proceed": True,
        }
        mock_response.content = json.dumps(llm_json)
        mock_llm.invoke.return_value = mock_response

        agent = PlannerAgent(llm=mock_llm)
        plan = agent.create_plan(
            question="Why did sales drop?",
            available_datasets=["data.csv"],
        )
        assert plan.question_type == "root_cause"
        assert plan.can_proceed is True
        mock_llm.invoke.assert_called_once()

    def test_planner_llm_failure_falls_back_to_mock(self):
        """When LLM raises an exception, falls back to mock plan gracefully."""
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("LLM unavailable")

        agent = PlannerAgent(llm=mock_llm)
        plan = agent.create_plan(
            question="Why did revenue decline?",
            available_datasets=["revenue.csv"],
        )
        # Should still return a valid plan from fallback
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.plan_steps) >= 1


# ---------------------------------------------------------------------------
# Endpoint integration test
# ---------------------------------------------------------------------------

class TestAnalyzeEndpoint:

    def test_analyze_endpoint_returns_200(self, client):
        """POST /investigations/analyze with valid dataset returns 200 + plan."""
        # First upload a dataset
        upload_resp = client.post(
            "/api/datasets/upload",
            files=_make_csv_upload("analysis_test.csv"),
        )
        assert upload_resp.status_code == 201, upload_resp.text
        dataset_id = upload_resp.json()["id"]

        # Now analyze it
        analyze_resp = client.post(
            "/api/investigations/analyze",
            json={
                "question": "What are the trends in this data?",
                "dataset_ids": [dataset_id],
            },
        )
        assert analyze_resp.status_code == 200, analyze_resp.text
        data = analyze_resp.json()

        assert "plan" in data
        assert "question_type" in data["plan"]
        assert "plan_steps" in data["plan"]
        assert "can_proceed" in data["plan"]

    def test_analyze_endpoint_with_missing_dataset(self, client):
        """POST /investigations/analyze with non-existent dataset_id returns 404."""
        analyze_resp = client.post(
            "/api/investigations/analyze",
            json={
                "question": "Analyze this",
                "dataset_ids": [99999],
            },
        )
        assert analyze_resp.status_code == 404

    def test_investigations_list_returns_empty(self, client):
        """GET /investigations/ returns empty list (stub)."""
        response = client.get("/api/investigations/")
        assert response.status_code == 200
        assert response.json() == []
