"""
End-to-end integration tests verifying the full workflow of IDAA.
"""
import io
import json
from app.models.investigation import InvestigationStatus


def test_complete_investigation_workflow(client) -> None:
    """
    Verifies the end-to-end user flow:
    Upload dataset -> Start investigation -> Verify details -> Generate report -> Chat
    """
    # 1. Upload CSV
    csv_data = b"Sales,Region,ProductID\n100,North,P1\n120,North,P2\n150,South,P1\n80,East,P2"
    file_payload = {"file": ("sales.csv", io.BytesIO(csv_data), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=file_payload)
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["id"]

    # 2. Verify dataset lists
    list_res = client.get("/api/datasets/")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 3. Start investigation
    analyze_payload = {
        "question": "Why did sales fluctuate?",
        "dataset_ids": [dataset_id]
    }
    analyze_res = client.post("/api/investigations/analyze", json=analyze_payload)
    assert analyze_res.status_code == 200
    
    plan_data = analyze_res.json()
    assert "plan" in plan_data
    assert "analysis" in plan_data
    assert len(plan_data["analysis"]) == 1

    # 4. Fetch investigation details from DB
    inv_list_res = client.get("/api/investigations/")
    assert inv_list_res.status_code == 200
    investigations = inv_list_res.json()
    assert len(investigations) >= 1
    
    inv_id = investigations[0]["id"]
    inv_detail_res = client.get(f"/api/investigations/{inv_id}")
    assert inv_detail_res.status_code == 200
    inv_details = inv_detail_res.json()
    assert inv_details["question"] == "Why did sales fluctuate?"
    assert len(inv_details["hypotheses"]) > 0

    # 5. Generate report
    report_res = client.post("/api/reports/generate", json={"investigation_id": inv_id})
    assert report_res.status_code == 201
    report_data = report_res.json()
    assert report_data["investigation_id"] == inv_id
    assert len(report_data["root_causes"]) > 0

    # 6. Verify investigation is now COMPLETED
    updated_inv_res = client.get(f"/api/investigations/{inv_id}")
    assert updated_inv_res.json()["status"] == InvestigationStatus.COMPLETED.value

    # 7. Conversational Chat
    chat_res = client.post(
        "/api/reports/chat",
        json={"message": "Can you summarize the findings?", "investigation_id": inv_id}
    )
    assert chat_res.status_code == 200
    assert "response" in chat_res.json()


def test_investigation_continues_with_new_data(client) -> None:
    """
    Verifies that uploading a new dataset and continuing the investigation
    re-runs missing data checks and updates the session metadata.
    """
    # 1. Upload first dataset
    csv_1 = b"Sales,Region,ProductID\n100,North,P1"
    file_1 = {"file": ("sales.csv", io.BytesIO(csv_1), "text/csv")}
    upload_1 = client.post("/api/datasets/upload", files=file_1)
    dataset_1_id = upload_1.json()["id"]

    # 2. Start investigation
    analyze_payload = {
        "question": "Is demand drop seasonal?",
        "dataset_ids": [dataset_1_id]
    }
    analyze_res = client.post("/api/investigations/analyze", json=analyze_payload)
    plan_data = analyze_res.json()

    # Get investigation ID
    inv_list = client.get("/api/investigations/").json()
    inv_id = inv_list[0]["id"]

    # 3. Upload second dataset (e.g. inventory details)
    csv_2 = b"ProductID,AvailableStock\nP1,5\nP2,12"
    file_2 = {"file": ("inventory.csv", io.BytesIO(csv_2), "text/csv")}
    upload_2 = client.post("/api/datasets/upload", files=file_2)
    dataset_2_id = upload_2.json()["id"]

    # 4. Continue investigation
    continue_payload = {
        "investigation_id": inv_id,
        "new_dataset_ids": [dataset_2_id]
    }
    continue_res = client.post("/api/investigations/continue", json=continue_payload)
    assert continue_res.status_code == 200
    
    continue_data = continue_res.json()
    assert "new_validations" in continue_data
    assert continue_data["investigation"]["id"] == inv_id
    assert dataset_2_id in continue_data["investigation"]["dataset_ids"]
