import pytest
import kb
import app

@pytest.fixture
def optimal_report_results():
    return [
        {"key": "glucose_f", "name": "Fasting Glucose", "value": 85.0, "unit": "mg/dL", "status": "normal"},
        {"key": "hba1c", "name": "HbA1c", "value": 5.1, "unit": "%", "status": "normal"},
        {"key": "trig", "name": "Triglycerides", "value": 90.0, "unit": "mg/dL", "status": "normal"},
        {"key": "ldl", "name": "LDL Cholesterol", "value": 78.0, "unit": "mg/dL", "status": "normal"},
        {"key": "hdl", "name": "HDL Cholesterol", "value": 62.0, "unit": "mg/dL", "status": "normal"},
        {"key": "chol", "name": "Total Cholesterol", "value": 158.0, "unit": "mg/dL", "status": "normal"},
        {"key": "creatinine", "name": "Serum Creatinine", "value": 0.85, "unit": "mg/dL", "status": "normal"},
        {"key": "alt", "name": "ALT (SGPT)", "value": 22.0, "unit": "U/L", "status": "normal"},
        {"key": "albumin", "name": "Albumin", "value": 4.5, "unit": "g/dL", "status": "normal"},
        {"key": "hemoglobin", "name": "Hemoglobin", "value": 15.2, "unit": "g/dL", "status": "normal"},
        {"key": "wbc", "name": "WBC Count", "value": 6400.0, "unit": "/uL", "status": "normal"}
    ]

@pytest.fixture
def stressed_report_results():
    return [
        {"key": "glucose_f", "name": "Fasting Glucose", "value": 142.0, "unit": "mg/dL", "status": "high"},
        {"key": "hba1c", "name": "HbA1c", "value": 7.4, "unit": "%", "status": "high"},
        {"key": "trig", "name": "Triglycerides", "value": 260.0, "unit": "mg/dL", "status": "high"},
        {"key": "ldl", "name": "LDL Cholesterol", "value": 175.0, "unit": "mg/dL", "status": "high"},
        {"key": "hdl", "name": "HDL Cholesterol", "value": 34.0, "unit": "mg/dL", "status": "low"},
        {"key": "creatinine", "name": "Serum Creatinine", "value": 1.6, "unit": "mg/dL", "status": "high"},
        {"key": "alt", "name": "ALT (SGPT)", "value": 78.0, "unit": "U/L", "status": "high"},
        {"key": "hemoglobin", "name": "Hemoglobin", "value": 10.2, "unit": "g/dL", "status": "low"}
    ]

def test_optimal_phenoage_biological_advantage(optimal_report_results):
    res = kb.calculate_phenotypic_age_and_resilience(optimal_report_results, chronological_age=50, sex="male")
    assert res["chronological_age"] == 50
    # Superior cellular homeostasis should yield biological age below chronological age
    assert res["phenotypic_age"] < 50
    assert res["age_delta"] < 0
    assert res["vitality_status"] in ("youthful", "stable")
    assert res["composite_resilience"] >= 90.0

    # Verify 5 radar axes
    radar = res["radar_data"]
    assert len(radar["labels"]) == 5
    assert len(radar["patient_scores"]) == 5
    for s in radar["patient_scores"]:
        assert 80 <= s <= 100

def test_stressed_phenoage_accelerated_wear(stressed_report_results):
    res = kb.calculate_phenotypic_age_and_resilience(stressed_report_results, chronological_age=45, sex="male")
    assert res["chronological_age"] == 45
    # Stressed metabolic and renal markers should increase phenotypic age
    assert res["phenotypic_age"] > 45
    assert res["age_delta"] > 0
    assert res["vitality_status"] == "accelerated_wear"
    assert len(res["key_priorities"]) >= 1

def test_sparse_biomarkers_resilience():
    # Only 2 markers present
    sparse = [
        {"key": "hemoglobin", "name": "Hemoglobin", "value": 14.0, "unit": "g/dL", "status": "normal"},
        {"key": "glucose_f", "name": "Glucose", "value": 92.0, "unit": "mg/dL", "status": "normal"}
    ]
    res = kb.calculate_phenotypic_age_and_resilience(sparse, chronological_age=40)
    assert 18.0 <= res["phenotypic_age"] <= 80.0
    assert 20.0 <= res["composite_resilience"] <= 100.0

def test_phenoage_api_endpoint():
    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        # Create a test record
        sess = "phenoage_test_sess"
        up = client.post("/api/confirm/test_rep_1", json={
            "session_id": sess,
            "results": [
                {"key": "glucose_f", "name": "Fasting Glucose", "value": 88.0, "unit": "mg/dL", "status": "normal"},
                {"key": "chol", "name": "Cholesterol", "value": 170.0, "unit": "mg/dL", "status": "normal"},
                {"key": "creatinine", "name": "Creatinine", "value": 0.9, "unit": "mg/dL", "status": "normal"}
            ]
        })
        # If test_rep_1 not found, create a sample upload first
        from pathlib import Path
        sample_path = Path(__file__).resolve().parent.parent / "sample_report_1.png"
        with open(sample_path, "rb") as f:
            up = client.post("/api/upload", data={"file": f, "session_id": sess, "age": "48", "sex": "female"})
        assert up.status_code == 200
        rid = up.get_json()["id"]

        # Call /api/phenoage/<rid>
        res = client.get(f"/api/phenoage/{rid}?session_id={sess}")
        assert res.status_code == 200
        d = res.get_json()
        assert "phenotypic_age" in d
        assert "radar_data" in d
        assert "axes" in d
        assert len(d["axes"]) == 5
