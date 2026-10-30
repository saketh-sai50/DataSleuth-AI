"""
DataAnalystAgent: LangGraph-compatible node that analyzes datasets and generates insights.
"""
import json
from typing import Optional

import pandas as pd
import plotly.express as px
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Prompt Template (kept outside functions — never hardcoded inside logic)
# ---------------------------------------------------------------------------
ANALYSIS_PROMPT = """You are a data analyst. Given this dataset summary, generate 3-5 key business insights.

Dataset: {filename}
Shape: {rows} rows x {cols} columns
Column Types: {column_types}
Summary Statistics: {summary_stats}
User Question: {question}

Generate concise, business-focused insights. Be factual. Only describe what the data shows.

Return ONLY a JSON array of strings, e.g.: ["Insight 1", "Insight 2", "Insight 3"]"""


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------
class DataAnalysisResult(BaseModel):
    """Structured result returned by DataAnalystAgent.analyze()."""
    summary_stats: dict
    column_types: dict[str, str]
    null_counts: dict[str, int]
    kpis: dict
    chart_json: Optional[str] = None
    insights: list[str]
    row_count: int
    column_count: int


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class DataAnalystAgent:
    """
    Analyzes a tabular dataset and returns statistical summaries,
    column type classification, KPIs, a Plotly chart, and LLM-generated insights.
    """

    def __init__(self, llm: Optional[ChatOpenAI] = None) -> None:
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze(
        self,
        file_path: str,
        question: str,
        filename: str = "dataset",
        skip_insights: bool = False,
    ) -> DataAnalysisResult:
        """
        Run full analysis pipeline on a dataset file.

        Args:
            file_path: Absolute path to the CSV or XLSX file.
            question:  User's analytical question.
            filename:  Original filename for display / prompt context.
            skip_insights: Whether to bypass the LLM insight generation step.

        Returns:
            DataAnalysisResult populated with stats, types, chart, and insights.
        """
        df = self._load_dataframe(file_path)

        summary_stats = self._compute_summary_stats(df)
        column_types = self._detect_column_types(df)
        null_counts = {col: int(df[col].isnull().sum()) for col in df.columns}
        kpis = self._compute_kpis(df, column_types)
        chart_json = self._generate_chart(df, column_types, question)
        
        if skip_insights:
            insights = []
        else:
            insights = self._generate_insights(
                df=df,
                filename=filename,
                question=question,
                column_types=column_types,
                summary_stats=summary_stats,
            )


        return DataAnalysisResult(
            summary_stats=summary_stats,
            column_types=column_types,
            null_counts=null_counts,
            kpis=kpis,
            chart_json=chart_json,
            insights=insights,
            row_count=len(df),
            column_count=len(df.columns),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _load_dataframe(self, file_path: str) -> pd.DataFrame:
        """Load a CSV or XLSX into a DataFrame."""
        from pathlib import Path
        suffix = Path(file_path).suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(file_path)
        elif suffix == ".xlsx":
            return pd.read_excel(file_path, engine="openpyxl")
        else:
            raise ValueError(f"Unsupported file extension: {suffix}")

    def _compute_summary_stats(self, df: pd.DataFrame) -> dict:
        """Return df.describe() as a JSON-safe nested dict."""
        numeric_df = df.select_dtypes(include="number")
        if numeric_df.empty:
            return {}
        stats = numeric_df.describe().to_dict()
        # Convert numpy types to plain Python for JSON serialisation
        return {
            col: {k: float(v) for k, v in metrics.items()}
            for col, metrics in stats.items()
        }

    def _detect_column_types(self, df: pd.DataFrame) -> dict[str, str]:
        """
        Classify each column as 'numeric', 'categorical', or 'datetime'.
        """
        types: dict[str, str] = {}
        for col in df.columns:
            dtype = df[col].dtype
            if pd.api.types.is_numeric_dtype(dtype):
                types[col] = "numeric"
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                types[col] = "datetime"
            else:
                types[col] = "categorical"
        return types

    def _compute_kpis(
        self, df: pd.DataFrame, column_types: dict[str, str]
    ) -> dict:
        """
        Compute key metrics: top-5 values per categorical column,
        null % per column, and basic numeric aggregates.
        """
        kpis: dict = {}

        # Null percentage
        kpis["null_percent"] = {
            col: round(df[col].isnull().mean() * 100, 2) for col in df.columns
        }

        # Top values for categorical columns
        top_values: dict = {}
        for col, col_type in column_types.items():
            if col_type == "categorical":
                top_values[col] = df[col].value_counts().head(5).to_dict()
        kpis["top_values"] = top_values

        # Numeric aggregates
        numeric_agg: dict = {}
        for col, col_type in column_types.items():
            if col_type == "numeric":
                numeric_agg[col] = {
                    "min": float(df[col].min()) if not df[col].isnull().all() else None,
                    "max": float(df[col].max()) if not df[col].isnull().all() else None,
                    "mean": float(df[col].mean()) if not df[col].isnull().all() else None,
                }
        kpis["numeric_agg"] = numeric_agg

        return kpis

    def _generate_chart(
        self, df: pd.DataFrame, column_types: dict[str, str], question: str = ""
    ) -> Optional[str]:
        """
        Generate a Plotly chart (bar, pie, or line) and return it as a JSON string.
        Detects 'pie' in the question to produce a pie/donut chart.
        Returns None if no suitable columns exist.
        """
        try:
            numeric_cols = [c for c, t in column_types.items() if t == "numeric"]
            cat_cols = [c for c, t in column_types.items() if t == "categorical"]

            if not numeric_cols:
                return None

            y_col = numeric_cols[0]
            is_pie_request = "pie" in question.lower()

            if is_pie_request and cat_cols:
                # Pie chart: sum values by category
                x_col = cat_cols[0]
                agg = df.groupby(x_col)[y_col].sum().reset_index().head(10)
                fig = px.pie(agg, names=x_col, values=y_col, title=f"Share of {y_col} by {x_col}")
            elif cat_cols:
                # Bar chart: categorical x-axis, numeric y-axis
                x_col = cat_cols[0]
                agg = df.groupby(x_col)[y_col].mean().reset_index().head(20)
                fig = px.bar(agg, x=x_col, y=y_col, title=f"Average {y_col} by {x_col}")
            else:
                # Line chart over index
                fig = px.line(df.head(100), y=y_col, title=f"{y_col} over rows")

            return fig.to_json()

        except Exception as exc:
            logger.warning(f"Chart generation failed: {exc}")
            return None

    def _generate_insights(
        self,
        df: pd.DataFrame,
        filename: str,
        question: str,
        column_types: dict[str, str],
        summary_stats: dict,
    ) -> list[str]:
        """
        Call the LLM to generate business insights. Falls back to mock
        insights when no LLM is configured.
        """
        if self.llm is None:
            logger.info("No LLM configured — returning mock insights.")
            return self._mock_insights(df, column_types)

        prompt_text = ANALYSIS_PROMPT.format(
            filename=filename,
            rows=len(df),
            cols=len(df.columns),
            column_types=json.dumps(column_types),
            summary_stats=json.dumps(summary_stats),
            question=question,
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt_text)])
            raw = response.content.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            if isinstance(parsed, list):
                return [str(i) for i in parsed]
        except Exception as exc:
            logger.warning(f"LLM insight generation failed: {exc}")

        return self._mock_insights(df, column_types)

    def _mock_insights(
        self, df: pd.DataFrame, column_types: dict[str, str]
    ) -> list[str]:
        """Return deterministic mock insights when LLM is unavailable."""
        numeric_cols = [c for c, t in column_types.items() if t == "numeric"]
        cat_cols = [c for c, t in column_types.items() if t == "categorical"]
        insights = [
            f"The dataset contains {len(df):,} rows and {len(df.columns)} columns.",
            f"There are {len(numeric_cols)} numeric column(s): {', '.join(numeric_cols) or 'none'}.",
            f"There are {len(cat_cols)} categorical column(s): {', '.join(cat_cols) or 'none'}.",
        ]
        null_cols = [c for c in df.columns if df[c].isnull().any()]
        if null_cols:
            insights.append(f"Columns with missing values: {', '.join(null_cols)}.")
        else:
            insights.append("No missing values detected across all columns.")
        return insights
