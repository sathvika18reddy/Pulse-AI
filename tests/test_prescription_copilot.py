import pytest
import kb
import app as flask_app
import json

def test_metformin_active_b12_depletion():
    results = [
        {"key": "b12", "name": "Vitamin B12", "value": 165.0, "unit": "pg/mL", "ref_low": 200.0, "ref_high": 900.0, "status": "low"},
        {"key": "glucose_f", "name": "Fasting Glucose", "value": 110.0, "unit": "mg/dL", "ref_low": 70.0, "ref_high": 100.0, "status": "high"}
    ]
    audit = kb.audit_prescription_and_depletions(results, medications=["Metformin 1000mg BID"])
    
    assert audit["total_medications_audited"] == 1
    assert len(audit["active_depletions"]) == 1
    
    b12_dep = audit["active_depletions"][0]
    assert b12_dep["nutrient_key"] == "b12"
    assert "Vitamin B12" in b12_dep["nutrient_name"]
    assert b12_dep["status"] == "low"
    assert b12_dep["severity"] == "high"
    assert "Metformin" in b12_dep["drug_class_name"]
    assert "terminal ileum" in b12_dep["mechanism"]
    assert "ADA" in b12_dep["evidence_citation"]
    
    # Folate should be identified as a surveillance gap since it was not measured
    gap_keys = [g["nutrient_key"] for g in audit["surveillance_gaps"]]
    assert "folate" in gap_keys
    
    # Doctor discussion script should contain B12 inquiry
    assert len(audit["doctor_discussion_script"]) >= 2
    b12_script = [q for q in audit["doctor_discussion_script"] if "B12" in q["title"]][0]
    assert b12_script["priority"] == "high"
    assert "Metformin" in b12_script["title"]

def test_statin_benign_transaminase_shift():
    results = [
        {"key": "alt", "name": "ALT (SGPT)", "value": 62.0, "unit": "U/L", "ref_low": 7.0, "ref_high": 40.0, "status": "high"},
        {"key": "chol", "name": "Total Cholesterol", "value": 175.0, "unit": "mg/dL", "ref_low": 0.0, "ref_high": 200.0, "status": "normal"}
    ]
    audit = kb.audit_prescription_and_depletions(results, medications=["Atorvastatin 40mg at bedtime"])
    
    assert audit["total_medications_audited"] == 1
    assert len(audit["benign_shifts"]) == 1
    
    alt_shift = audit["benign_shifts"][0]
    assert alt_shift["marker_key"] == "alt"
    assert "Hepatic Adaptation" in alt_shift["reassurance_badge"]
    assert "ACC/AHA" in alt_shift["guideline"]
    assert "3×" in alt_shift["label"] or "3x" in alt_shift["label"]
    
    # CoQ10 should be in surveillance gaps
    gap_keys = [g["nutrient_key"] for g in audit["surveillance_gaps"]]
    assert "coq10" in gap_keys
    assert "vitd" in gap_keys

def test_ace_inhibitor_benign_creatinine_bump():
    results = [
        {"key": "creatinine", "name": "Serum Creatinine", "value": 1.35, "unit": "mg/dL", "ref_low": 0.7, "ref_high": 1.2, "status": "high"},
        {"key": "potassium", "name": "Potassium", "value": 4.9, "unit": "mmol/L", "ref_low": 3.5, "ref_high": 5.0, "status": "normal"}
    ]
    audit = kb.audit_prescription_and_depletions(results, medications=["Lisinopril 20mg"])
    
    assert audit["total_medications_audited"] == 1
    # Creatinine elevation of 1.35 vs 1.2 is +12.5%, well within <= 30% margin
    shift_markers = [s["marker_key"] for s in audit["benign_shifts"]]
    assert "creatinine" in shift_markers
    
    cr_shift = [s for s in audit["benign_shifts"] if s["marker_key"] == "creatinine"][0]
    assert "30%" in cr_shift["label"]
    assert "KDIGO" in cr_shift["guideline"]
    
    # Zinc should be in surveillance gaps
    gap_keys = [g["nutrient_key"] for g in audit["surveillance_gaps"]]
    assert "zinc" in gap_keys

def test_ppi_magnesium_depletion():
    results = [
        {"key": "magnesium", "name": "Serum Magnesium", "value": 1.3, "unit": "mg/dL", "ref_low": 1.7, "ref_high": 2.4, "status": "low"}
    ]
    audit = kb.audit_prescription_and_depletions(results, medications=["Omeprazole 40mg daily"])
    
    assert audit["total_medications_audited"] == 1
    assert len(audit["active_depletions"]) == 1
    mag_dep = audit["active_depletions"][0]
    assert mag_dep["nutrient_key"] == "magnesium"
    assert "FDA" in mag_dep["evidence_citation"]
    
    # Unmeasured PPI nutrients should be gaps
    gap_keys = [g["nutrient_key"] for g in audit["surveillance_gaps"]]
    assert "b12" in gap_keys
    assert "iron" in gap_keys
    assert "calcium" in gap_keys

def test_empty_and_unmatched_medications():
    results = [{"key": "glucose_f", "value": 90.0, "status": "normal"}]
    
    audit_empty = kb.audit_prescription_and_depletions(results, medications=[])
    assert audit_empty["total_medications_audited"] == 0
    assert audit_empty["has_findings"] is False
    assert "No active prescription medications" in audit_empty["summary"]
    
    audit_unmatched = kb.audit_prescription_and_depletions(results, medications=["Biotin 5000mcg", "Vitamin C"])
    assert audit_unmatched["total_medications_audited"] == 0
    assert audit_unmatched["has_findings"] is False

def test_api_endpoints_medication_audit():
    client = flask_app.app.test_client()
    
    # Create or retrieve a sample report
    reports_res = client.get("/api/reports")
    data = json.loads(reports_res.data)
    if not data:
        pytest.skip("No reports available in test environment")
        
    rid = data[0]["id"]
    
    # 1. Test GET endpoint
    get_res = client.get(f"/api/medications/audit/{rid}")
    assert get_res.status_code == 200
    audit_get = json.loads(get_res.data)
    assert "active_depletions" in audit_get
    assert "surveillance_gaps" in audit_get
    assert "benign_shifts" in audit_get
    assert "doctor_discussion_script" in audit_get
    
    # 2. Test POST endpoint with interactive simulation
    sim_payload = {
        "medications": ["Metformin 1000mg", "Atorvastatin 20mg", "Lisinopril 10mg"]
    }
    post_res = client.post(
        f"/api/medications/audit/{rid}",
        data=json.dumps(sim_payload),
        content_type="application/json"
    )
    assert post_res.status_code == 200
    audit_post = json.loads(post_res.data)
    assert audit_post["total_medications_audited"] == 3
    assert len(audit_post["doctor_discussion_script"]) > 0

