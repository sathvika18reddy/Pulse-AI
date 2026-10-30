import pytest
import json
import analyzer
import app as flask_app

def test_diff_resolved_and_improving_markers():
    base_rep = {
        "id": "base01",
        "date": "10/01/2026",
        "filename": "Lab_Jan.pdf",
        "results": [
            {"key": "glucose_f", "name": "Fasting Glucose", "value": 145.0, "unit": "mg/dL", "status": "high", "category": "Diabetes"},
            {"key": "chol", "name": "Total Cholesterol", "value": 240.0, "unit": "mg/dL", "status": "high", "category": "Lipid"},
            {"key": "hdl", "name": "HDL Cholesterol", "value": 35.0, "unit": "mg/dL", "status": "low", "category": "Lipid"},
            {"key": "vitd", "name": "Vitamin D", "value": 15.0, "unit": "ng/mL", "status": "low", "category": "Vitamins"},
            {"key": "wbc", "name": "WBC Count", "value": 6500.0, "unit": "/uL", "status": "normal", "category": "CBC"}
        ]
    }
    
    curr_rep = {
        "id": "curr02",
        "date": "10/04/2026",
        "filename": "Lab_Apr.pdf",
        "results": [
            {"key": "glucose_f", "name": "Fasting Glucose", "value": 94.0, "unit": "mg/dL", "status": "normal", "category": "Diabetes"}, # Resolved
            {"key": "chol", "name": "Total Cholesterol", "value": 208.0, "unit": "mg/dL", "status": "high", "category": "Lipid"},       # Improving (-13.3%)
            {"key": "hdl", "name": "HDL Cholesterol", "value": 44.0, "unit": "mg/dL", "status": "normal", "category": "Lipid"},         # Resolved
            {"key": "vitd", "name": "Vitamin D", "value": 27.0, "unit": "ng/mL", "status": "low", "category": "Vitamins"},               # Improving (+80.0%)
            {"key": "wbc", "name": "WBC Count", "value": 6800.0, "unit": "/uL", "status": "normal", "category": "CBC"}                  # Stable
        ]
    }
    
    diff = analyzer.compute_report_diff(base_rep, curr_rep)
    
    assert diff["elapsed_days"] == 90
    assert "90 days" in diff["elapsed_str"]
    assert diff["counts"]["resolved"] == 2
    assert diff["counts"]["improving"] == 2
    assert diff["counts"]["stable"] == 1
    assert diff["counts"]["worsening"] == 0
    assert diff["counts"]["new_alert"] == 0
    
    # 2 resolved (2.0) + 2 improving (1.5) out of 4 baseline abnormals = 3.5 / 4 = 87.5%
    assert diff["therapeutic_response_score"] >= 80.0
    assert diff["therapeutic_tier"] == "excellent"
    assert "Outstanding" in diff["therapeutic_badge"]
    assert "Fasting Glucose" in diff["narrative"]
    
    # Check individual trajectory badges
    glu_diff = [d for d in diff["differences"] if d["key"] == "glucose_f"][0]
    assert glu_diff["trajectory"] == "resolved"
    assert glu_diff["delta"] == -51.0
    assert "Normalized" in glu_diff["trajectory_badge"]

def test_diff_new_alerts_and_worsening():
    base_rep = {
        "id": "base_healthy",
        "date": "01/02/2026",
        "results": [
            {"key": "potassium", "name": "Potassium", "value": 4.2, "unit": "mmol/L", "status": "normal", "category": "Electrolytes"},
            {"key": "creatinine", "name": "Creatinine", "value": 0.9, "unit": "mg/dL", "status": "normal", "category": "Kidney"},
            {"key": "hba1c", "name": "HbA1c", "value": 6.8, "unit": "%", "status": "high", "category": "Diabetes"}
        ]
    }
    
    curr_rep = {
        "id": "curr_deteriorating",
        "date": "01/05/2026",
        "results": [
            {"key": "potassium", "name": "Potassium", "value": 5.8, "unit": "mmol/L", "status": "high", "category": "Electrolytes"}, # New Alert
            {"key": "creatinine", "name": "Creatinine", "value": 1.6, "unit": "mg/dL", "status": "high", "category": "Kidney"},      # New Alert
            {"key": "hba1c", "name": "HbA1c", "value": 8.4, "unit": "%", "status": "high", "category": "Diabetes"}                    # Worsening
        ]
    }
    
    diff = analyzer.compute_report_diff(base_rep, curr_rep)
    
    assert diff["counts"]["new_alert"] == 2
    assert diff["counts"]["worsening"] == 1
    assert diff["counts"]["resolved"] == 0
    assert diff["counts"]["improving"] == 0
    assert diff["therapeutic_response_score"] < 40.0
    assert diff["therapeutic_tier"] == "suboptimal"
    assert "Suboptimal" in diff["therapeutic_badge"]

def test_diff_added_and_omitted_markers():
    base_rep = {
        "id": "b1",
        "results": [
            {"key": "hemoglobin", "name": "Hemoglobin", "value": 14.0, "status": "normal"},
            {"key": "tsh", "name": "TSH", "value": 2.5, "status": "normal"}
        ]
    }
    
    curr_rep = {
        "id": "c1",
        "results": [
            {"key": "hemoglobin", "name": "Hemoglobin", "value": 14.2, "status": "normal"},
            {"key": "b12", "name": "Vitamin B12", "value": 450.0, "status": "normal"}
        ]
    }
    
    diff = analyzer.compute_report_diff(base_rep, curr_rep)
    
    assert len(diff["differences"]) == 1 # hemoglobin
    assert len(diff["added_markers"]) == 1
    assert diff["added_markers"][0]["key"] == "b12"
    assert len(diff["omitted_markers"]) == 1
    assert diff["omitted_markers"][0]["key"] == "tsh"

def test_api_endpoints_report_diff():
    client = flask_app.app.test_client()
    
    reports_res = client.get("/api/reports")
    data = json.loads(reports_res.data)
    if len(data) < 2:
        pytest.skip("Requires at least 2 reports in the database")
        
    latest_rid = data[0]["id"]
    prior_rid = data[1]["id"]
    
    # 1. Test GET /api/diff/<rid>
    res_diff = client.get(f"/api/diff/{latest_rid}")
    assert res_diff.status_code == 200
    payload = json.loads(res_diff.data)
    assert payload["has_baseline"] is True
    assert "diff" in payload
    assert "therapeutic_response_score" in payload["diff"]
    assert "counts" in payload["diff"]
    
    # 2. Test GET /api/diff/<rid>/baselines
    res_baselines = client.get(f"/api/diff/{latest_rid}/baselines")
    assert res_baselines.status_code == 200
    base_payload = json.loads(res_baselines.data)
    assert "candidates" in base_payload
    assert len(base_payload["candidates"]) >= 1
    
    # 3. Test POST /api/diff/<rid> with specific baseline
    post_diff = client.post(
        f"/api/diff/{latest_rid}",
        data=json.dumps({"baseline_id": prior_rid}),
        content_type="application/json"
    )
    assert post_diff.status_code == 200
    post_payload = json.loads(post_diff.data)
    assert post_payload["has_baseline"] is True
    assert post_payload["baseline_id"] == prior_rid
