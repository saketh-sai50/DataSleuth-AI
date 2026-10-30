"""
Unit tests for ReportAgent, ReportService, and reports API endpoints.
"""
import json
import pytest
from app.models.investigation import Investigation, InvestigationStatus
from app.models.dataset import Dataset
from app.models.report import Report


def _create_mock_investigation(db_session) -> Investigation:
    """Helper to seed a mock investigation."""
    dataset = Dataset(
        filename="test_sales.csv",
        stored_filename="test_sales_uuid.csv",
        file_path="uploads/test_sales_uuid.csv",
        file_type="csv",
        row_count=100,
        column_count=5,
        schema_info=json.dumps({"Sales": "numeric", "Region": "categorical"}),
        file_size_bytes=1024,
    )
    db_session.add(dataset)
    db_session.commit()

    investigation = Investigation(
        question="Why did sales drop in March?",
        status=InvestigationStatus.ANALYZING.value,
        hypotheses_json=json.dumps([
            {
                "id": "h1",
                "title": "Seasonal demand drop",
                "description": "Historical sales drop in March",
                "prior_probability": "MEDIUM",
                "validation_data_needed": ["marketing.csv"],
                "is_validated": False,
            }
        ]),
        validations_json=json.dumps([
            {
                "hypothesis_id": "h1",
                "can_validate": "PARTIAL",
                "validation_status": "Need marketing dataset to fully validate",
                "missing_dataset": "marketing.csv",
                "missing_columns": ["Budget", "CampaignID"],
                "follow_up_question": "Do you have marketing campaign data?",
            }
        ]),
        missing_datasets_json=json.dumps(["marketing.csv"]),
        follow_up_questions_json=json.dumps(["Do you have marketing campaign data?"]),
    )
    db_session.add(investigation)
    db_session.commit()

    # Link dataset
    from app.models.investigation import InvestigationDataset
    link = InvestigationDataset(investigation_id=investigation.id, dataset_id=dataset.id)
    db_session.add(link)
    db_session.commit()

    return investigation


def test_generate_report_returns_response(client, db_session) -> None:
    """Test generating a report through the POST /reports/generate endpoint."""
    inv = _create_mock_investigation(db_session)

    res = client.post("/api/reports/generate", json={"investigation_id": inv.id})
    assert res.status_code == 201
    
    data = res.json()
    assert data["investigation_id"] == inv.id
    assert "executive_summary" in data
    assert isinstance(data["root_causes"], list)
    assert len(data["root_causes"]) > 0
    assert 0.0 <= data["overall_confidence"] <= 1.0


def test_report_persisted_in_db(client, db_session) -> None:
    """Test retrieving the generated report by ID and verify persistence."""
    inv = _create_mock_investigation(db_session)

    gen_res = client.post("/api/reports/generate", json={"investigation_id": inv.id})
    report_id = gen_res.json()["id"]

    res = client.get(f"/api/reports/{report_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == report_id
    assert data["executive_summary"] == gen_res.json()["executive_summary"]


def test_list_reports(client, db_session) -> None:
    """Test retrieving list of all generated reports."""
    inv = _create_mock_investigation(db_session)
    
    client.post("/api/reports/generate", json={"investigation_id": inv.id})

    res = client.get("/api/reports/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1


def test_generate_report_invalid_investigation(client) -> None:
    """Test that generating a report for a non-existent investigation returns 404."""
    res = client.post("/api/reports/generate", json={"investigation_id": 99999})
    assert res.status_code == 404


def test_chat_returns_response(client) -> None:
    """Test POST /reports/chat returns assistant response and suggestions."""
    res = client.post("/api/reports/chat", json={"message": "Can you summarize my data?"})
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert "suggested_actions" in data
    assert isinstance(data["suggested_actions"], list)


def test_chat_with_investigation_context(client, db_session) -> None:
    """Test POST /reports/chat with investigation_id includes context successfully."""
    inv = _create_mock_investigation(db_session)
    res = client.post(
        "/api/reports/chat",
        json={"message": "What is missing?", "investigation_id": inv.id}
    )
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert data["investigation_id"] == inv.id
