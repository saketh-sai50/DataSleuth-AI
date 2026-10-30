"""
ReportAgent: Generates business reports and handles chat context.
"""
import json
from datetime import datetime
from typing import Optional, Any
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel


REPORT_PROMPT = """You are a senior business analyst writing an executive investigation report.

Investigation Question: {question}

Available Evidence:
{evidence_summary}

Validated Hypotheses:
{validated_hypotheses}

Unvalidated Hypotheses (insufficient data):
{unvalidated_hypotheses}

Missing Data:
{missing_data}

Write a professional business investigation report. Focus on business value, not technical details. Be concise and professional.
Respond ONLY with a JSON object matching this structure:
{{
  "executive_summary": "string",
  "root_causes": [
    {{"hypothesis_id": "string", "cause": "string", "confidence": 0.75, "evidence": "string"}}
  ],
  "evidence": ["list of evidence statements"],
  "limitations": ["list of limitations"],
  "recommendations": ["list of recommendations"],
  "missing_info": ["list of missing information items"],
  "next_steps": ["list of next steps"],
  "overall_confidence": 0.65
}}"""


CHAT_PROMPT = """You are a precise data analyst assistant. Answer the user's question using ONLY the data provided in the context below.

CRITICAL RULES:
1. If "[Database Query Results]" are present in the context, you MUST use those EXACT numbers to answer. Do NOT perform your own calculations. Do NOT estimate. Do NOT use averages or summaries from elsewhere.
2. If no database query results are present, use the dataset statistics provided, but be clear about what you are approximating.
3. Never make up numbers. Never hallucinate. If you genuinely cannot answer from the provided data, say exactly what data is missing.
4. Provide clear, direct, business-friendly answers. Be concise.

=== CONTEXT START ===
{context}
=== CONTEXT END ===

User Question: {message}

Respond ONLY with a JSON object:
{{
  "response": "Your clear, factual answer here",
  "suggested_actions": ["Follow-up action 1", "Follow-up action 2"]
}}"""


class ReportAgent:
    """
    Generates structured reports using LLM or mock fallback.
    """

    def __init__(self, llm: Optional[ChatOpenAI] = None) -> None:
        self.llm = llm

    def generate_report(
        self,
        question: str,
        hypotheses: list[dict[str, Any]],
        validations: list[dict[str, Any]],
        analysis_results: list[dict[str, Any]],
        missing_datasets: list[str]
    ) -> dict[str, Any]:
        """
        Generates a business report based on investigation details.
        """
        if self.llm is None:
            logger.info("No LLM configured — returning mock report.")
            return self._mock_report(question)

        evidence_summary = self._build_evidence_summary(analysis_results)
        validated_hypotheses = self._build_validated_hypotheses(hypotheses, validations)
        unvalidated_hypotheses = self._build_unvalidated_hypotheses(hypotheses, validations)
        missing_data = ", ".join(missing_datasets) if missing_datasets else "None"

        prompt_text = REPORT_PROMPT.format(
            question=question,
            evidence_summary=evidence_summary,
            validated_hypotheses=validated_hypotheses,
            unvalidated_hypotheses=unvalidated_hypotheses,
            missing_data=missing_data,
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt_text)])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            return parsed
        except Exception as exc:
            logger.warning(f"LLM report generation failed: {exc}")
            return self._mock_report(question)

    def chat(
        self,
        message: str,
        context: str = ""
    ) -> dict[str, Any]:
        """
        Answers user chat queries.
        """
        if self.llm is None:
            logger.info("No LLM configured — returning mock chat.")
            return self._mock_chat(message)

        prompt_text = CHAT_PROMPT.format(
            context=context,
            message=message
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt_text)])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            return parsed
        except Exception as exc:
            logger.warning(f"LLM chat failed: {exc}")
            return self._mock_chat(message)

    def _build_evidence_summary(self, analysis_results: list[dict[str, Any]]) -> str:
        summary_lines = []
        for i, res in enumerate(analysis_results):
            insights = res.get("insights", [])
            summary_lines.append(f"Dataset {i+1} Insights: " + "; ".join(insights))
        return "\n".join(summary_lines) if summary_lines else "No evidence available."

    def _build_validated_hypotheses(self, hypotheses: list[dict[str, Any]], validations: list[dict[str, Any]]) -> str:
        validated = []
        val_map = {val["hypothesis_id"]: val for val in validations}
        for hyp in hypotheses:
            hyp_id = hyp.get("id")
            val = val_map.get(hyp_id)
            if val and val.get("can_validate") in ["YES", "PARTIAL"]:
                validated.append(f"- {hyp.get('title')}: {hyp.get('description')} (Validation Status: {val.get('validation_status')})")
        return "\n".join(validated) if validated else "None"

    def _build_unvalidated_hypotheses(self, hypotheses: list[dict[str, Any]], validations: list[dict[str, Any]]) -> str:
        unvalidated = []
        val_map = {val["hypothesis_id"]: val for val in validations}
        for hyp in hypotheses:
            hyp_id = hyp.get("id")
            val = val_map.get(hyp_id)
            if not val or val.get("can_validate") == "NO":
                unvalidated.append(f"- {hyp.get('title')}: {hyp.get('description')} (Data Missing: {val.get('missing_dataset') if val else 'Unknown'})")
        return "\n".join(unvalidated) if unvalidated else "None"

    def _mock_report(self, question: str) -> dict[str, Any]:
        return {
            "executive_summary": f"Investigation into '{question}' completed. The available datasets suggest key trends in operational parameters, with moderate overall confidence.",
            "root_causes": [
                {
                    "hypothesis_id": "h1",
                    "cause": "Seasonal demand fluctuations affecting transaction volumes",
                    "confidence": 0.8,
                    "evidence": "Data shows a regular fluctuation matching historical seasonality parameters."
                },
                {
                    "hypothesis_id": "h2",
                    "cause": "Marketing spend optimization changes",
                    "confidence": 0.6,
                    "evidence": "Analysis shows variance in acquisition cost metric averages."
                }
            ],
            "evidence": [
                "Consistent average transaction value identified in numeric analysis",
                "Highest transaction frequencies occur during standard business hours"
            ],
            "limitations": [
                "Lack of daily marketing campaign spend details prevents direct ROI attribution",
                "Missing inventory stock levels limits stockout impact confirmation"
            ],
            "recommendations": [
                "Align promotional schedules with peak seasonal window peaks",
                "Establish alert parameters for stock level changes"
            ],
            "missing_info": [
                "Inventory dataset: stock level status by Product ID",
                "Marketing spend dataset: campaign level budget details"
            ],
            "next_steps": [
                "Acquire missing inventory dataset for direct cross-reference validation",
                "Incorporate returns data to analyze net margin changes"
            ],
            "overall_confidence": 0.7
        }

    def _mock_chat(self, message: str) -> dict[str, Any]:
        return {
            "response": f"Based on the investigation context, your question about '{message}' is noted. The current analysis indicates solid transaction baselines, but further verification requires cross-referencing additional context.",
            "suggested_actions": [
                "View investigation timeline",
                "Generate current report",
                "Upload missing datasets"
            ]
        }
