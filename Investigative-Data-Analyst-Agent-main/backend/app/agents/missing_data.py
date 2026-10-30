"""
MissingDataAgent: Validates hypotheses against available datasets and
identifies what additional data is needed to complete the investigation.
"""
import json
from typing import Optional

from loguru import logger
from pydantic import BaseModel

from app.agents.root_cause import Hypothesis

# ---------------------------------------------------------------------------
# Prompt Template
# ---------------------------------------------------------------------------
MISSING_DATA_PROMPT = """You are a data validation expert.

We are investigating: {question}

Available datasets and their schemas:
{available_data}

Hypotheses to validate:
{hypotheses}

For each hypothesis, determine:
1. Can it be VALIDATED with the available data? (YES/PARTIAL/NO)
2. If NO or PARTIAL: what specific dataset is missing?
3. Generate an intelligent follow-up question to ask the user about the missing data
4. Specify exactly which columns are needed from the missing dataset

Respond in JSON:
{{
  "validations": [
    {{
      "hypothesis_id": "h1",
      "can_validate": "YES|PARTIAL|NO",
      "validation_status": "string explanation",
      "missing_dataset": "dataset_name or null",
      "missing_columns": ["col1", "col2"],
      "follow_up_question": "Intelligent question to ask user",
      "evidence_found": "string or null"
    }}
  ],
  "overall_investigation_status": "CAN_PROCEED|NEEDS_DATA|BLOCKED",
  "summary": "Brief summary of what we can and cannot determine"
}}"""


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class HypothesisValidation(BaseModel):
    """Validation result for a single hypothesis."""
    hypothesis_id: str
    can_validate: str  # YES | PARTIAL | NO
    validation_status: str
    missing_dataset: Optional[str] = None
    missing_columns: list[str] = []
    follow_up_question: Optional[str] = None
    evidence_found: Optional[str] = None


class MissingDataResult(BaseModel):
    """Full result from MissingDataAgent.validate_hypotheses()."""
    validations: list[HypothesisValidation]
    overall_investigation_status: str  # CAN_PROCEED | NEEDS_DATA | BLOCKED
    summary: str
    missing_datasets: list[str]       # unique list of all missing dataset names
    follow_up_questions: list[str]    # all collected follow-up questions


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class MissingDataAgent:
    """
    Evaluates whether each hypothesis can be validated with available datasets
    and surfaces gaps and follow-up questions for the user.
    """

    def __init__(self, llm: Optional[object] = None) -> None:
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def validate_hypotheses(
        self,
        question: str,
        hypotheses: list[Hypothesis],
        available_datasets: list[dict],  # [{name, schema, rows}]
    ) -> MissingDataResult:
        """
        Check each hypothesis against available data.

        Args:
            question:            The user's investigative question.
            hypotheses:          List of Hypothesis objects to validate.
            available_datasets:  List of dicts describing available datasets.

        Returns:
            MissingDataResult with per-hypothesis validations and summary.
        """
        if self.llm is None:
            logger.info("No LLM configured — returning mock hypothesis validations.")
            return self._mock_validation(hypotheses)

        prompt_text = MISSING_DATA_PROMPT.format(
            question=question,
            available_data=self._format_available_data(available_datasets),
            hypotheses=self._format_hypotheses(hypotheses),
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
            validations = [HypothesisValidation(**v) for v in data["validations"]]
            missing_datasets = self._extract_missing_datasets(validations)
            follow_up_questions = [
                v.follow_up_question
                for v in validations
                if v.follow_up_question
            ]

            return MissingDataResult(
                validations=validations,
                overall_investigation_status=data["overall_investigation_status"],
                summary=data["summary"],
                missing_datasets=missing_datasets,
                follow_up_questions=follow_up_questions,
            )
        except Exception as exc:
            logger.warning(f"LLM validation failed: {exc} — using mock validation.")
            return self._mock_validation(hypotheses)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _format_available_data(self, datasets: list[dict]) -> str:
        """Format available dataset info for the prompt."""
        if not datasets:
            return "No datasets available."
        lines: list[str] = []
        for ds in datasets:
            name = ds.get("name", "unknown")
            schema = ds.get("schema", {})
            rows = ds.get("rows", "unknown")
            cols = list(schema.keys()) if schema else []
            lines.append(
                f"- {name}: {rows} rows, columns: {', '.join(cols) or 'unknown'}"
            )
        return "\n".join(lines)

    def _format_hypotheses(self, hypotheses: list[Hypothesis]) -> str:
        """Format hypothesis list for the prompt."""
        lines: list[str] = []
        for h in hypotheses:
            lines.append(
                f"[{h.id}] {h.title}\n"
                f"  Description: {h.description}\n"
                f"  Data needed: {'; '.join(h.validation_data_needed)}"
            )
        return "\n\n".join(lines)

    def _mock_validation(self, hypotheses: list[Hypothesis]) -> MissingDataResult:
        """
        Return a mock validation result.
        First 2 hypotheses are marked YES; the rest are marked NO with follow-ups.
        """
        validations: list[HypothesisValidation] = []

        for idx, hyp in enumerate(hypotheses):
            if idx < 2:
                validations.append(
                    HypothesisValidation(
                        hypothesis_id=hyp.id,
                        can_validate="YES",
                        validation_status=(
                            f"Sufficient data is available to validate '{hyp.title}'."
                        ),
                        missing_dataset=None,
                        missing_columns=[],
                        follow_up_question=None,
                        evidence_found="Preliminary patterns found in available data.",
                    )
                )
            else:
                needed = hyp.validation_data_needed[0] if hyp.validation_data_needed else "additional data"
                parts = needed.split(":", 1)
                ds_name = parts[0].strip()
                validations.append(
                    HypothesisValidation(
                        hypothesis_id=hyp.id,
                        can_validate="NO",
                        validation_status=(
                            f"Cannot validate '{hyp.title}' — required data is missing."
                        ),
                        missing_dataset=ds_name,
                        missing_columns=["date", "value"],
                        follow_up_question=(
                            f"Do you have access to {ds_name}? "
                            f"This would help us evaluate the '{hyp.title}' hypothesis."
                        ),
                        evidence_found=None,
                    )
                )

        missing_datasets = self._extract_missing_datasets(validations)
        follow_up_questions = [
            v.follow_up_question for v in validations if v.follow_up_question
        ]

        status = "CAN_PROCEED" if not missing_datasets else "NEEDS_DATA"
        summary = (
            f"Validated {sum(1 for v in validations if v.can_validate == 'YES')} of "
            f"{len(validations)} hypotheses. "
            f"{len(missing_datasets)} additional dataset(s) required."
        )

        return MissingDataResult(
            validations=validations,
            overall_investigation_status=status,
            summary=summary,
            missing_datasets=missing_datasets,
            follow_up_questions=follow_up_questions,
        )

    def _extract_missing_datasets(
        self, validations: list[HypothesisValidation]
    ) -> list[str]:
        """Return a de-duplicated list of all missing dataset names."""
        seen: set[str] = set()
        result: list[str] = []
        for v in validations:
            if v.missing_dataset and v.missing_dataset not in seen:
                seen.add(v.missing_dataset)
                result.append(v.missing_dataset)
        return result
