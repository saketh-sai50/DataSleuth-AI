"""
RootCauseAgent: Generates structured business hypotheses for investigative questions.
"""
import json
from datetime import datetime
from typing import Optional

from loguru import logger
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Prompt Template
# ---------------------------------------------------------------------------
ROOT_CAUSE_PROMPT = """You are a senior business analyst investigating a business problem.

Business Question: {question}

Dataset Context:
{dataset_context}

Generate 5-8 possible root cause hypotheses for this business question.
For EACH hypothesis:
- Give it a clear title
- Explain what could have caused it
- Rate your prior probability (LOW/MEDIUM/HIGH) that this is the actual cause
- Identify what data would be needed to validate it

IMPORTANT: Do NOT validate hypotheses. Only generate possibilities based on business knowledge.
Do NOT assume any hypothesis is true.

Respond in JSON:
{{
  "hypotheses": [
    {{
      "id": "h1",
      "title": "string",
      "description": "string",
      "prior_probability": "LOW|MEDIUM|HIGH",
      "validation_data_needed": ["dataset_name: description"]
    }}
  ]
}}"""


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class Hypothesis(BaseModel):
    """A single root cause hypothesis with metadata."""
    id: str
    title: str
    description: str
    prior_probability: str  # LOW | MEDIUM | HIGH
    validation_data_needed: list[str]
    is_validated: bool = False
    evidence: Optional[str] = None
    confidence_score: Optional[float] = None  # 0.0 – 1.0 after validation


class RootCauseResult(BaseModel):
    """Full result returned by RootCauseAgent.generate_hypotheses()."""
    question: str
    hypotheses: list[Hypothesis]
    generated_at: datetime


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class RootCauseAgent:
    """
    Generates structured root cause hypotheses for a business question.
    Falls back to mock hypotheses when no LLM is configured.
    """

    def __init__(self, llm: Optional[object] = None) -> None:
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_hypotheses(
        self,
        question: str,
        dataset_context: str,
    ) -> RootCauseResult:
        """
        Generate root cause hypotheses for the given business question.

        Args:
            question:        The user's investigative question.
            dataset_context: Formatted string describing available datasets.

        Returns:
            RootCauseResult containing a list of Hypothesis objects.
        """
        if self.llm is None:
            logger.info("No LLM configured — returning mock root cause hypotheses.")
            return self._mock_hypotheses(question)

        prompt_text = ROOT_CAUSE_PROMPT.format(
            question=question,
            dataset_context=dataset_context,
        )

        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=prompt_text)])
            raw = response.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            data = json.loads(raw.strip())
            hypotheses = [Hypothesis(**h) for h in data["hypotheses"]]
            return RootCauseResult(
                question=question,
                hypotheses=hypotheses,
                generated_at=datetime.utcnow(),
            )
        except Exception as exc:
            logger.warning(f"LLM hypothesis generation failed: {exc} — using mock.")
            return self._mock_hypotheses(question)

    def _build_dataset_context(self, datasets: list[dict]) -> str:
        """
        Format a list of dataset info dicts into a readable context string.

        Args:
            datasets: List of dicts with keys: name, schema, rows (optional).

        Returns:
            Multi-line string describing each dataset.
        """
        if not datasets:
            return "No datasets available."

        lines: list[str] = []
        for ds in datasets:
            name = ds.get("name", "unknown")
            schema = ds.get("schema", {})
            rows = ds.get("rows", "unknown")
            cols = list(schema.keys()) if schema else []
            lines.append(
                f"Dataset: {name}\n"
                f"  Rows: {rows}\n"
                f"  Columns: {', '.join(cols) or 'unknown'}"
            )
        return "\n\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _mock_hypotheses(self, question: str) -> RootCauseResult:
        """Return 5 realistic business hypotheses when no LLM is available."""
        hypotheses = [
            Hypothesis(
                id="h1",
                title="Seasonal demand pattern",
                description=(
                    "Revenue or key metrics may be declining due to predictable "
                    "seasonal fluctuations. Consumer behaviour shifts during certain "
                    "months or quarters can temporarily depress demand without "
                    "indicating a structural problem."
                ),
                prior_probability="HIGH",
                validation_data_needed=[
                    "sales_history: Month-over-month and year-over-year sales data",
                    "calendar_data: Holiday and seasonal event calendar",
                ],
            ),
            Hypothesis(
                id="h2",
                title="Pricing strategy change",
                description=(
                    "A recent adjustment to product or service pricing — whether a "
                    "price increase, removal of discounts, or change to pricing tiers "
                    "— may have reduced conversion rates or driven customers to "
                    "competitors."
                ),
                prior_probability="MEDIUM",
                validation_data_needed=[
                    "pricing_history: Historical price points by product/SKU",
                    "conversion_data: Conversion rates before and after price changes",
                ],
            ),
            Hypothesis(
                id="h3",
                title="Supply chain disruption",
                description=(
                    "Delays or shortages from suppliers could be causing fulfilment "
                    "issues, leading to cancellations, lower customer satisfaction, "
                    "and reduced repeat purchases."
                ),
                prior_probability="MEDIUM",
                validation_data_needed=[
                    "inventory_data: Stock levels and reorder frequency",
                    "fulfilment_data: Order fulfilment rate and lead times",
                ],
            ),
            Hypothesis(
                id="h4",
                title="Competitor market entry",
                description=(
                    "A new or aggressive competitor may have entered the market, "
                    "attracting customers with lower prices, superior features, or "
                    "better marketing, resulting in market share loss."
                ),
                prior_probability="LOW",
                validation_data_needed=[
                    "market_share_data: Market share trends over time",
                    "competitor_pricing: Competitor price benchmarking data",
                ],
            ),
            Hypothesis(
                id="h5",
                title="Marketing spend reduction",
                description=(
                    "A cut in marketing or advertising budget may have reduced brand "
                    "visibility and customer acquisition, leading to lower top-of-funnel "
                    "traffic and declining new customer numbers."
                ),
                prior_probability="MEDIUM",
                validation_data_needed=[
                    "marketing_spend: Historical marketing expenditure by channel",
                    "traffic_data: Website or store traffic data over time",
                ],
            ),
        ]
        return RootCauseResult(
            question=question,
            hypotheses=hypotheses,
            generated_at=datetime.utcnow(),
        )
