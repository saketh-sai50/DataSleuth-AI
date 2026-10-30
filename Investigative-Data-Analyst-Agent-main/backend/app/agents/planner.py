"""
PlannerAgent: LangGraph-compatible node that creates structured investigation plans.
"""
import json
from typing import Optional

from langchain_core.messages import HumanMessage
from loguru import logger
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Prompt Template
# ---------------------------------------------------------------------------
PLANNER_PROMPT = """You are a senior business analyst and investigation planner.

The user has asked: {question}

Available datasets: {datasets}

Create a structured investigation plan with these steps:
1. Identify what type of question this is (trend analysis, root cause, comparison, etc.)
2. List required analysis steps in order
3. Identify what data is needed for each step
4. Flag any obvious data gaps

Respond in JSON with this structure:
{{
  "question_type": "string",
  "plan_steps": [{{"step": 1, "action": "string", "requires": ["dataset_names"]}}],
  "required_datasets": ["list of dataset names needed"],
  "available_datasets": ["list of datasets that are available"],
  "missing_datasets": ["list of datasets that are needed but not available"],
  "can_proceed": true/false
}}"""


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------
class ExecutionPlan(BaseModel):
    """Structured investigation plan produced by the PlannerAgent."""
    question_type: str
    plan_steps: list[dict]
    required_datasets: list[str]
    available_datasets: list[str]
    missing_datasets: list[str]
    can_proceed: bool


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class PlannerAgent:
    """
    Generates a structured investigation execution plan from a user question
    and a list of available dataset names.
    """

    def __init__(self, llm: Optional[object] = None) -> None:
        self.llm = llm

    def create_plan(
        self,
        question: str,
        available_datasets: list[str],
    ) -> ExecutionPlan:
        """
        Generate an ExecutionPlan for the given question.

        Args:
            question:           The user's investigative question.
            available_datasets: Names of datasets currently in the system.

        Returns:
            ExecutionPlan with steps, required datasets, and gap analysis.
        """
        if self.llm is None:
            logger.info("No LLM configured — returning mock execution plan.")
            return self._mock_plan(question, available_datasets)

        prompt_text = PLANNER_PROMPT.format(
            question=question,
            datasets=json.dumps(available_datasets),
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt_text)])
            raw = response.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            plan_data = json.loads(raw.strip())
            return ExecutionPlan(**plan_data)
        except Exception as exc:
            logger.warning(f"LLM plan generation failed: {exc} — using mock plan.")
            return self._mock_plan(question, available_datasets)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _mock_plan(
        self,
        question: str,
        available_datasets: list[str],
    ) -> ExecutionPlan:
        """
        Return a deterministic mock plan used when no LLM is available.
        Detects simple keywords to infer question type.
        """
        q_lower = question.lower()
        if "trend" in q_lower or "over time" in q_lower:
            question_type = "trend_analysis"
        elif "compare" in q_lower or "vs" in q_lower or "versus" in q_lower:
            question_type = "comparison"
        elif "why" in q_lower or "root cause" in q_lower:
            question_type = "root_cause"
        else:
            question_type = "exploratory_analysis"

        required = available_datasets if available_datasets else ["dataset"]
        missing = [d for d in required if d not in available_datasets]

        plan_steps = [
            {
                "step": 1,
                "action": "Load and validate dataset(s)",
                "requires": required,
            },
            {
                "step": 2,
                "action": "Compute summary statistics and detect column types",
                "requires": required,
            },
            {
                "step": 3,
                "action": f"Perform {question_type} relevant to: {question}",
                "requires": required,
            },
            {
                "step": 4,
                "action": "Generate visualisations and synthesise insights",
                "requires": required,
            },
        ]

        return ExecutionPlan(
            question_type=question_type,
            plan_steps=plan_steps,
            required_datasets=required,
            available_datasets=available_datasets,
            missing_datasets=missing,
            can_proceed=len(missing) == 0,
        )
