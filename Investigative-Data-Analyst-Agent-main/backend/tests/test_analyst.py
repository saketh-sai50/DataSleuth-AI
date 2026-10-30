"""
Tests for DataAnalystAgent — uses real pandas DataFrames, mocks the LLM.
"""
import io
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.agents.data_analyst import DataAnalystAgent, DataAnalysisResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_csv_path(tmp_path: Path) -> str:
    """Write a small CSV to a temp file and return its path."""
    df = pd.DataFrame({
        "product": ["Widget", "Gadget", "Doohickey", "Widget", "Gadget"],
        "sales": [100, 250, 75, 180, 310],
        "region": ["North", "South", "East", "West", "North"],
        "price": [9.99, 19.99, 4.99, 9.99, 19.99],
    })
    csv_file = tmp_path / "sample.csv"
    df.to_csv(str(csv_file), index=False)
    return str(csv_file)


@pytest.fixture()
def csv_with_nulls_path(tmp_path: Path) -> str:
    """Write a CSV containing null values."""
    df = pd.DataFrame({
        "name": ["Alice", None, "Charlie"],
        "score": [95.0, None, 87.0],
        "grade": ["A", "B", None],
    })
    csv_file = tmp_path / "nulls.csv"
    df.to_csv(str(csv_file), index=False)
    return str(csv_file)


@pytest.fixture()
def agent_no_llm() -> DataAnalystAgent:
    """DataAnalystAgent without LLM — uses mock insights."""
    return DataAnalystAgent(llm=None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDataAnalystAgent:

    def test_analyze_returns_summary_stats(self, agent_no_llm, sample_csv_path):
        """summary_stats must contain numeric column entries."""
        result: DataAnalysisResult = agent_no_llm.analyze(
            file_path=sample_csv_path,
            question="What are the top selling products?",
            filename="sample.csv",
        )
        assert isinstance(result.summary_stats, dict)
        assert len(result.summary_stats) > 0
        # 'sales' and 'price' are numeric — should appear in describe()
        assert "sales" in result.summary_stats or "price" in result.summary_stats

    def test_analyze_detects_column_types(self, agent_no_llm, sample_csv_path):
        """column_types must classify numeric and categorical columns."""
        result: DataAnalysisResult = agent_no_llm.analyze(
            file_path=sample_csv_path,
            question="Analyse the data",
        )
        assert isinstance(result.column_types, dict)
        assert result.column_types.get("sales") == "numeric"
        assert result.column_types.get("product") == "categorical"

    def test_analyze_detects_nulls(self, agent_no_llm, csv_with_nulls_path):
        """null_counts must correctly count NaN values per column."""
        result: DataAnalysisResult = agent_no_llm.analyze(
            file_path=csv_with_nulls_path,
            question="Are there missing values?",
        )
        assert isinstance(result.null_counts, dict)
        assert result.null_counts.get("name", 0) == 1
        assert result.null_counts.get("score", 0) == 1
        assert result.null_counts.get("grade", 0) == 1

    def test_analyze_generates_chart(self, agent_no_llm, sample_csv_path):
        """chart_json must be a valid JSON string (Plotly figure)."""
        result: DataAnalysisResult = agent_no_llm.analyze(
            file_path=sample_csv_path,
            question="Show me a chart",
        )
        assert result.chart_json is not None
        parsed = json.loads(result.chart_json)
        assert isinstance(parsed, dict)
        # Plotly JSON always has 'data' and 'layout'
        assert "data" in parsed

    def test_analyze_returns_row_and_column_count(self, agent_no_llm, sample_csv_path):
        """row_count and column_count should match the actual DataFrame shape."""
        result: DataAnalysisResult = agent_no_llm.analyze(
            file_path=sample_csv_path,
            question="How many rows?",
        )
        assert result.row_count == 5
        assert result.column_count == 4

    def test_analyze_returns_insights(self, agent_no_llm, sample_csv_path):
        """insights list must be non-empty with string entries."""
        result: DataAnalysisResult = agent_no_llm.analyze(
            file_path=sample_csv_path,
            question="Give me insights",
        )
        assert isinstance(result.insights, list)
        assert len(result.insights) >= 1
        assert all(isinstance(i, str) for i in result.insights)

    def test_analyze_with_mock_llm(self, sample_csv_path):
        """When LLM is configured, its response is used for insights."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '["Insight A", "Insight B", "Insight C"]'
        mock_llm.invoke.return_value = mock_response

        agent = DataAnalystAgent(llm=mock_llm)
        result = agent.analyze(
            file_path=sample_csv_path,
            question="LLM test question",
            filename="sample.csv",
        )
        assert result.insights == ["Insight A", "Insight B", "Insight C"]
        mock_llm.invoke.assert_called_once()

    def test_analyze_kpis_populated(self, agent_no_llm, sample_csv_path):
        """kpis dict must include null_percent, top_values, and numeric_agg keys."""
        result: DataAnalysisResult = agent_no_llm.analyze(
            file_path=sample_csv_path,
            question="KPI check",
        )
        assert "null_percent" in result.kpis
        assert "top_values" in result.kpis
        assert "numeric_agg" in result.kpis
