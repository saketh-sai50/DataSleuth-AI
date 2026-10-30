"""
AnalystService: orchestrates dataset retrieval and delegates to DataAnalystAgent.
"""
from typing import Optional

from sqlalchemy.orm import Session
from loguru import logger

from app.agents.data_analyst import DataAnalystAgent, DataAnalysisResult
from app.core.config import settings
from app.repositories.dataset_repository import DatasetRepository


def _build_llm() -> Optional[object]:
    """
    Instantiate a ChatOpenAI client only when an API key is available.
    Returns None in environments without credentials (e.g. CI, local dev).
    """
    if not settings.OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY not set — LLM calls will be skipped.")
        return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            temperature=0.2,
        )
    except Exception as exc:
        logger.error(f"Failed to initialise ChatOpenAI: {exc}")
        return None


class AnalystService:
    """
    Service that wraps DataAnalystAgent, providing dataset lookup
    and LLM lifecycle management.
    """

    def __init__(self) -> None:
        llm = _build_llm()
        self._agent = DataAnalystAgent(llm=llm)

    def analyze_dataset(
        self,
        dataset_id: int,
        question: str,
        db: Session,
        skip_insights: bool = False,
    ) -> DataAnalysisResult:
        """
        Retrieve a dataset record from the DB and run analysis.

        Args:
            dataset_id: Primary key of the Dataset to analyse.
            question:   The user's analytical question.
            db:         Active SQLAlchemy session (injected).
            skip_insights: Whether to bypass generating new LLM insights.

        Returns:
            DataAnalysisResult with stats, chart, and insights.

        Raises:
            ValueError: If the dataset_id does not exist.
        """
        repo = DatasetRepository(db)
        dataset = repo.get_by_id(dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset with id={dataset_id} not found.")

        logger.info(
            f"Analysing dataset id={dataset_id} filename={dataset.filename!r} "
            f"question={question!r}"
        )

        return self._agent.analyze(
            file_path=dataset.file_path,
            question=question,
            filename=dataset.filename,
            skip_insights=skip_insights,
        )

