import pytest
import analyzer

def test_drug_lab_interactions():
    # Patient taking Atorvastatin (Statin) with mildly elevated ALT
    row_alt = {"key": "alt", "name": "ALT (SGPT)", "value": 52.0, "unit": "U/L", "ref_low": 7.0, "ref_high": 40.0, "category": "Liver"}
    flagged = analyzer.flag(row_alt, medications=["Atorvastatin 20mg", "Aspirin"])
    assert flagged["status"] == "high"
    assert flagged["medication_interaction"] is not None
    assert flagged["medication_interaction"]["drug_class"] == "statin"
    assert "atorvastatin" in flagged["medication_interaction"]["matched_name"]
    assert "AHA/ACC" in flagged["medication_interaction"]["guideline"]
    
    # Patient taking Lisinopril (ACE inhibitor) with Potassium
    row_k = {"key": "potassium", "name": "Potassium", "value": 5.2, "unit": "mmol/L", "ref_low": 3.5, "ref_high": 5.0, "category": "Electrolytes"}
    flagged_k = analyzer.flag(row_k, medications=["Lisinopril 10mg"])
    assert flagged_k["status"] == "high"
    assert flagged_k["medication_interaction"] is not None
    assert flagged_k["medication_interaction"]["drug_class"] == "ace_inhibitor"
    assert "KDIGO" in flagged_k["medication_interaction"]["guideline"]
    
    # Patient taking Metformin with borderline B12
    row_b12 = {"key": "b12", "name": "Vitamin B12", "value": 180.0, "unit": "pg/mL", "ref_low": 200.0, "ref_high": 900.0, "category": "Vitamins"}
    flagged_b12 = analyzer.flag(row_b12, medications=["Metformin 500mg bid"])
    assert flagged_b12["medication_interaction"] is not None
    assert flagged_b12["medication_interaction"]["drug_class"] == "metformin"

def test_pregnancy_trimester_adjustments():
    # Hemoglobin in 2nd trimester: physiological hemodilution lowers normal threshold to 10.5 g/dL
    # Value 10.8 g/dL is low for non-pregnant adult, but normal in 2nd trimester!
    row_hb = {"key": "hemoglobin", "name": "Hemoglobin", "value": 10.8, "unit": "g/dL", "ref_low": None, "ref_high": None, "category": "CBC"}
    
    # Non-pregnant female default (12.0 - 15.5) -> 10.8 is low
    res_normal = analyzer.flag(row_hb, sex="female")
    assert res_normal["status"] == "low"
    assert res_normal["ref_low"] == 12.0
    
    # Pregnant 2nd trimester (10.5 - 14.5) -> 10.8 is normal!
    res_preg = analyzer.flag(row_hb, sex="female", pregnancy_trimester=2)
    assert res_preg["status"] == "normal"
    assert res_preg["ref_low"] == 10.5
    assert res_preg["pregnancy_adjusted"] is True
