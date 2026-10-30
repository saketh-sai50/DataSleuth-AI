"""
InvestigationService: Orchestrates the full investigation workflow across
PlannerAgent, DataAnalystAgent, RootCauseAgent, and MissingDataAgent.
"""
import json
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.agents.data_analyst import DataAnalysisResult
from app.agents.missing_data import MissingDataAgent, MissingDataResult
from app.agents.planner import ExecutionPlan, PlannerAgent
from app.agents.root_cause import Hypothesis, RootCauseAgent, RootCauseResult
from app.core.config import settings
from app.models.investigation import Investigation, InvestigationStatus
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.services.analyst_service import AnalystService


def _build_llm() -> Optional[object]:
    """Instantiate a ChatOpenAI client when API key is available."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            temperature=0.1,
        )
    except Exception as exc:
        logger.error(f"Failed to initialise LLM: {exc}")
        return None


class InvestigationService:
    """
    Orchestrates the end-to-end investigation lifecycle:
    planning → data analysis → hypothesis generation → validation.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._llm = _build_llm()
        self._inv_repo = InvestigationRepository(db)
        self._ds_repo = DatasetRepository(db)
        self._analyst = AnalystService()
        self._planner = PlannerAgent(llm=self._llm)
        self._root_cause = RootCauseAgent(llm=self._llm)
        self._missing_data = MissingDataAgent(llm=self._llm)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start_investigation(
        self,
        question: str,
        dataset_ids: list[int],
    ) -> tuple[Investigation, ExecutionPlan, list[DataAnalysisResult], RootCauseResult, MissingDataResult]:
        """
        Run the full investigation workflow for a new question.

        Steps:
          1. Create Investigation record (INITIATED)
          2. Validate and link datasets
          3. Run PlannerAgent
          4. Run DataAnalystAgent on each dataset
          5. Run RootCauseAgent with dataset context
          6. Run MissingDataAgent to validate hypotheses
          7. Persist results and update status

        Returns:
            Tuple of (investigation, plan, analysis_results, root_cause, missing_data).

        Raises:
            ValueError: If any dataset_id does not exist.
        """
        # 1. Create investigation record
        investigation = self._inv_repo.create(question)
        logger.info(f"Starting investigation id={investigation.id} question={question!r}")

        try:
            # 2. Validate & link datasets
            datasets = self._load_and_link_datasets(investigation.id, dataset_ids)

            available_names = [ds.filename for ds in datasets]

            # 3. Planning phase
            plan = self._planner.create_plan(
                question=question,
                available_datasets=available_names,
            )
            logger.info(f"Plan created: question_type={plan.question_type!r}")

            # 4. Analysis phase
            analysis_results: list[DataAnalysisResult] = []
            for ds in datasets:
                try:
                    result = self._analyst.analyze_dataset(
                        dataset_id=ds.id,
                        question=question,
                        db=self.db,
                    )
                    analysis_results.append(result)
                except Exception as exc:
                    logger.error(f"Analysis failed for dataset id={ds.id}: {exc}")

            # 5. Root-cause hypotheses (only if diagnostic question type)
            dataset_dicts = self._build_dataset_dicts(datasets, analysis_results)
            is_root_cause_type = (
                plan.question_type == "root_cause"
                or "why" in question.lower()
                or "cause" in question.lower()
                or "reason" in question.lower()
                or "drop" in question.lower()
                or "decrease" in question.lower()
                or "increase" in question.lower()
            )

            if is_root_cause_type:
                root_cause_agent = RootCauseAgent(llm=self._llm)
                context = root_cause_agent._build_dataset_context(dataset_dicts)
                root_cause_result = self._root_cause.generate_hypotheses(
                    question=question,
                    dataset_context=context,
                )
                hypotheses = root_cause_result.hypotheses
            else:
                hypotheses = []
                from datetime import datetime
                root_cause_result = RootCauseResult(
                    question=question,
                    hypotheses=[],
                    generated_at=datetime.utcnow(),
                )


            # Persist hypotheses
            hypotheses_json = json.dumps(
                [h.model_dump() for h in hypotheses]
            )
            self._inv_repo.update_hypotheses(investigation.id, hypotheses_json)

            # 6. Missing data validation
            if hypotheses:
                missing_data_result = self._missing_data.validate_hypotheses(
                    question=question,
                    hypotheses=hypotheses,
                    available_datasets=dataset_dicts,
                )
            else:
                from app.agents.missing_data import MissingDataResult
                missing_data_result = MissingDataResult(
                    validations=[],
                    overall_investigation_status="CAN_PROCEED",
                    summary="All required data is available for this exploratory question.",
                    missing_datasets=[],
                    follow_up_questions=[],
                )

            # 7. Persist validations and update status
            validations_json = json.dumps(
                [v.model_dump() for v in missing_data_result.validations]
            )
            missing_json = json.dumps(missing_data_result.missing_datasets)
            questions_json = json.dumps(missing_data_result.follow_up_questions)

            self._inv_repo.update_validations(
                investigation.id, validations_json, missing_json, questions_json
            )


            new_status = (
                InvestigationStatus.WAITING_FOR_DATA.value
                if missing_data_result.missing_datasets
                else InvestigationStatus.ANALYZING.value
            )
            investigation = self._inv_repo.update_status(investigation.id, new_status)

            return investigation, plan, analysis_results, root_cause_result, missing_data_result

        except Exception as exc:
            logger.error(f"Investigation id={investigation.id} failed: {exc}")
            self._inv_repo.update_status(investigation.id, InvestigationStatus.FAILED.value)
            raise

    def continue_investigation(
        self,
        investigation_id: int,
        new_dataset_ids: list[int],
    ) -> tuple[Investigation, MissingDataResult]:
        """
        Add new datasets to an existing investigation and re-run validation.

        Args:
            investigation_id: ID of the existing investigation.
            new_dataset_ids:  IDs of newly uploaded datasets to incorporate.

        Returns:
            Tuple of (updated_investigation, new_missing_data_result).

        Raises:
            ValueError: If the investigation or any dataset is not found.
        """
        investigation = self._inv_repo.get_by_id(investigation_id)
        if investigation is None:
            raise ValueError(f"Investigation id={investigation_id} not found.")

        logger.info(f"Continuing investigation id={investigation_id}")

        # Link new datasets
        for did in new_dataset_ids:
            ds = self._ds_repo.get_by_id(did)
            if ds is None:
                raise ValueError(f"Dataset id={did} not found.")
            self._inv_repo.add_dataset(investigation_id, did)

        # Load ALL datasets (old + new)
        all_links = self._inv_repo.get_datasets(investigation_id)
        all_dataset_ids = [link.dataset_id for link in all_links]
        all_datasets = [
            self._ds_repo.get_by_id(did)
            for did in all_dataset_ids
            if self._ds_repo.get_by_id(did) is not None
        ]

        # Reconstruct hypotheses from JSON
        hypotheses: list[Hypothesis] = []
        if investigation.hypotheses_json:
            try:
                raw_hypotheses = json.loads(investigation.hypotheses_json)
                hypotheses = [Hypothesis(**h) for h in raw_hypotheses]
            except Exception as exc:
                logger.warning(f"Failed to parse hypotheses_json: {exc}")

        # Build dataset context dicts
        dataset_dicts = [
            {"name": ds.filename, "schema": {}, "rows": ds.row_count}
            for ds in all_datasets
            if ds is not None
        ]

        # Re-run missing data validation with all datasets
        missing_data_result = self._missing_data.validate_hypotheses(
            question=investigation.question,
            hypotheses=hypotheses,
            available_datasets=dataset_dicts,
        )

        # Persist updated validations
        validations_json = json.dumps(
            [v.model_dump() for v in missing_data_result.validations]
        )
        missing_json = json.dumps(missing_data_result.missing_datasets)
        questions_json = json.dumps(missing_data_result.follow_up_questions)

        self._inv_repo.update_validations(
            investigation_id, validations_json, missing_json, questions_json
        )

        new_status = (
            InvestigationStatus.WAITING_FOR_DATA.value
            if missing_data_result.missing_datasets
            else InvestigationStatus.ANALYZING.value
        )
        investigation = self._inv_repo.update_status(investigation_id, new_status)

        return investigation, missing_data_result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _load_and_link_datasets(self, investigation_id: int, dataset_ids: list[int]):
        """
        Validate that each dataset exists, then link to investigation.

        Returns:
            List of Dataset ORM objects.

        Raises:
            ValueError: If any dataset_id is not found.
        """
        datasets = []
        for did in dataset_ids:
            ds = self._ds_repo.get_by_id(did)
            if ds is None:
                raise ValueError(f"Dataset id={did} not found.")
            self._inv_repo.add_dataset(investigation_id, did)
            datasets.append(ds)
        return datasets

    def _build_dataset_dicts(
        self,
        datasets,
        analysis_results: list[DataAnalysisResult],
    ) -> list[dict]:
        """Build lightweight dataset info dicts for agent context."""
        result = []
        for idx, ds in enumerate(datasets):
            schema = {}
            rows = ds.row_count or 0
            if idx < len(analysis_results):
                schema = analysis_results[idx].column_types
                rows = analysis_results[idx].row_count
            result.append({
                "name": ds.filename,
                "schema": schema,
                "rows": rows,
            })
        return result
