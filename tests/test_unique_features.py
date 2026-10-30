import pytest, json
import kb, agent, app

@pytest.fixture
def client():
    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        yield client

def test_cardiometabolic_indices_calculation():
    results = [
        {"key": "glucose_f", "name": "Fasting Glucose", "value": 140.0, "status": "high"},
        {"key": "trig", "name": "Triglycerides", "value": 240.0, "status": "high"},
        {"key": "hdl", "name": "HDL Cholesterol", "value": 35.0, "status": "low"},
        {"key": "creatinine", "name": "Creatinine", "value": 1.4, "status": "high"}
    ]
    
    data = kb.calculate_cardiometabolic_indices(results, sex="male", age=52)
    indices = data["indices"]
    
    # 1. TyG Index: ln(240 * 140 / 2) = ln(16800) ~= 9.73 -> high risk
    assert "tyg_index" in indices
    assert indices["tyg_index"]["value"] == 9.73
    assert indices["tyg_index"]["risk"] == "high"
    
    # 2. AIP Index: log10((240/88.57) / (35/38.67)) ~= log10(2.7097 / 0.905) ~= log10(2.99) ~= 0.48 -> high risk
    assert "aip" in indices
    assert indices["aip"]["risk"] == "high"
    assert indices["aip"]["value"] > 0.40
    
    # 3. Calculated eGFR (CKD-EPI 2021)
    assert "calculated_egfr" in indices
    assert 50.0 <= indices["calculated_egfr"]["value"] <= 70.0
    
    # 4. Active Syndrome Detection
    syndromes = data["active_syndromes"]
    assert any(s["id"] == "metabolic_syndrome" for s in syndromes)

def test_what_if_lifestyle_simulator():
    baseline_results = [
        {"key": "glucose_f", "name": "Fasting Glucose", "value": 135.0, "unit": "mg/dL", "ref_low": 70.0, "ref_high": 100.0, "status": "high"},
        {"key": "hba1c", "name": "HbA1c", "value": 7.4, "unit": "%", "ref_low": 4.0, "ref_high": 5.6, "status": "high"},
        {"key": "trig", "name": "Triglycerides", "value": 220.0, "unit": "mg/dL", "ref_low": 0.0, "ref_high": 150.0, "status": "high"},
        {"key": "ldl", "name": "LDL Cholesterol", "value": 160.0, "unit": "mg/dL", "ref_low": 0.0, "ref_high": 100.0, "status": "high"}
    ]
    
    # Scenario: 5% weight loss + 150 min exercise + statin therapy
    interventions = {
        "weight_loss_pct": 5.0,
        "exercise_150min": True,
        "statin_therapy": True
    }
    
    projected = kb.simulate_lifestyle_interventions(baseline_results, interventions)
    proj_map = {p["key"]: p for p in projected}
    
    # Glucose drops by ~12 mg/dL from weight loss and 8 mg/dL from exercise
    assert proj_map["glucose_f"]["projected_value"] < 135.0
    assert proj_map["glucose_f"]["net_change"] < 0
    
    # HbA1c drops by ~0.4% from weight loss and 0.5% from exercise
    assert proj_map["hba1c"]["projected_value"] < 7.4
    
    # LDL drops significantly with statin
    assert proj_map["ldl"]["projected_value"] < 110.0
    assert any("statin" in m.lower() for m in proj_map["ldl"]["evidence_mechanisms"])

def test_sbar_clinical_brief_generation():
    sample_report = {
        "filename": "Metabolic_Labs.pdf",
        "date": "2026-10-22",
        "patient_sex": "male",
        "patient_age": 55,
        "results": [
            {"key": "glucose_f", "name": "Fasting Glucose", "value": 160.0, "unit": "mg/dL", "status": "high", "is_critical": False, "category": "Diabetes", "meaning": "Suggests diabetes."},
            {"key": "hba1c", "name": "HbA1c", "value": 8.1, "unit": "%", "status": "high", "is_critical": False, "category": "Diabetes", "meaning": "Elevated 3-month average."}
        ]
    }
    profile = {
        "medications": ["Metformin 500mg"],
        "conditions": ["Hypertension"]
    }
    
    sbar = agent.generate_sbar_brief(sample_report, profile)
    assert "situation" in sbar
    assert "background" in sbar
    assert "assessment" in sbar
    assert "recommendation" in sbar
    assert "Metformin" in sbar["background"]
    assert "Endocrinologist" in sbar["recommendation"] or "Diabetologist" in sbar["recommendation"]

def test_consultation_rehearsal_dialogue_flow():
    sample_report = {
        "date": "2026-10-22",
        "results": [
            {"key": "hemoglobin", "name": "Hemoglobin", "value": 9.8, "unit": "g/dL", "status": "low"}
        ]
    }
    
    # Step 0: Doctor introduces anomalies and asks symptoms
    d0 = agent.rehearse_consultation(sample_report, step=0)
    assert d0["step"] == 0
    assert "Hemoglobin" in d0["doctor_dialogue"]
    assert not d0["is_final"]
    
    # Step 1: User answered symptoms, doctor asks medications
    d1 = agent.rehearse_consultation(sample_report, step=1, user_input="I have been feeling unusually fatigued and short of breath for 3 weeks.")
    assert d1["step"] == 1
    assert "medications" in d1["doctor_dialogue"].lower()
    assert d1["feedback_on_previous_answer"] != ""

def test_new_api_endpoints(client):
    # Test /api/profile
    prof_res = client.post("/api/profile", json={"session_id": "test_s99", "medications": ["Atorvastatin"], "conditions": ["Hyperlipidemia"]})
    assert prof_res.status_code == 200
    assert prof_res.get_json()["medications"] == ["Atorvastatin"]
    
    get_prof = client.get("/api/profile?session_id=test_s99")
    assert get_prof.status_code == 200
    assert get_prof.get_json()["medications"] == ["Atorvastatin"]
    
    # Test /api/timeline
    time_res = client.get("/api/timeline?session_id=test_s99")
    assert time_res.status_code == 200
    assert "trajectories" in time_res.get_json()
    
    # Test /api/feedback
    fb_res = client.post("/api/feedback", json={"rating": 5, "comment": "Excellent clinical accuracy."})
    assert fb_res.status_code == 200
    assert fb_res.get_json()["success"] is True
