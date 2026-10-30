import pytest
import analyzer
import kb

def test_analyzer_boundary_cases():
    # Hemoglobin default in KB is 13.0 - 17.0
    # Exactly on lower bound -> normal, severity none
    r_exact_low = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 13.0, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "category": "CBC"})
    assert r_exact_low["status"] == "normal"
    assert r_exact_low["severity"] == "none"
    assert r_exact_low["deviation_pct"] == 0.0
    assert r_exact_low["meaning"] == ""

    # Exactly on upper bound -> normal, severity none
    r_exact_high = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 17.0, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "category": "CBC"})
    assert r_exact_high["status"] == "normal"
    assert r_exact_high["severity"] == "none"
    assert r_exact_high["deviation_pct"] == 0.0

    # Mild low (< 10% below 13.0, e.g. 12.0 is (13-12)/13 = 7.7%)
    r_mild_low = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 12.0, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "category": "CBC"})
    assert r_mild_low["status"] == "low"
    assert r_mild_low["severity"] == "mild"
    assert r_mild_low["deviation_pct"] == 7.7
    assert "anaemia" in r_mild_low["meaning"].lower()

    # Moderate low (10-30% below 13.0, e.g. 10.8 is (13-10.8)/13 = 16.9%)
    r_mod_low = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 10.8, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "category": "CBC"})
    assert r_mod_low["status"] == "low"
    assert r_mod_low["severity"] == "moderate"
    assert r_mod_low["deviation_pct"] == 16.9

    # Marked low (> 30% below 13.0, e.g. 8.0 is (13-8)/13 = 38.5%)
    r_marked_low = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 8.0, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "category": "CBC"})
    assert r_marked_low["status"] == "low"
    assert r_marked_low["severity"] == "marked"
    assert r_marked_low["deviation_pct"] == 38.5

    # Mild high (< 10% above 17.0, e.g. 18.0 is (18-17)/17 = 5.9%)
    r_mild_high = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 18.0, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "category": "CBC"})
    assert r_mild_high["status"] == "high"
    assert r_mild_high["severity"] == "mild"
    assert r_mild_high["deviation_pct"] == 5.9
    assert "dehydration" in r_mild_high["meaning"].lower()

    # Moderate high (10-30% above 17.0, e.g. 20.0 is (20-17)/17 = 17.6%)
    r_mod_high = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 20.0, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "category": "CBC"})
    assert r_mod_high["status"] == "high"
    assert r_mod_high["severity"] == "moderate"
    assert r_mod_high["deviation_pct"] == 17.6

    # Marked high (> 30% above 17.0, e.g. 23.0 is (23-17)/17 = 35.3%)
    r_marked_high = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 23.0, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "category": "CBC"})
    assert r_marked_high["status"] == "high"
    assert r_marked_high["severity"] == "marked"
    assert r_marked_high["deviation_pct"] == 35.3

def test_printed_range_priority():
    # Report printed range wins over KB default
    # Fasting glucose default in KB: 70 - 100
    # Lab prints strict range: 70 - 90
    # Value 95 is normal in KB, but high according to the printed report!
    row = {"key": "glucose_f", "name": "Fasting Glucose", "value": 95.0, "unit": "mg/dL", "ref_low": 70.0, "ref_high": 90.0, "category": "Diabetes"}
    result = analyzer.flag(row)
    assert result["status"] == "high"
    assert result["ref_high"] == 90.0

def test_kb_default_fallback_when_none():
    # When report has None for printed range, falls back to KB defaults
    row = {"key": "chol", "name": "Total Cholesterol", "value": 210.0, "unit": "mg/dL", "ref_low": None, "ref_high": None, "category": "Lipid"}
    result = analyzer.flag(row)
    assert result["ref_low"] == 0.0
    assert result["ref_high"] == 200.0
    assert result["status"] == "high"

def test_sex_adjusted_ranges():
    # Hemoglobin: Male default is 13.0-17.0, Female default is 12.0-15.5
    # Value 12.5 is low for male, but normal for female!
    row_male = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 12.5, "unit": "g/dL", "ref_low": None, "ref_high": None, "category": "CBC"}, sex="male")
    assert row_male["status"] == "low"
    assert row_male["ref_low"] == 13.0

    row_female = analyzer.flag({"key": "hemoglobin", "name": "Hemoglobin", "value": 12.5, "unit": "g/dL", "ref_low": None, "ref_high": None, "category": "CBC"}, sex="female")
    assert row_female["status"] == "normal"
    assert row_female["ref_low"] == 12.0

def test_position_percentage():
    # Middle of range 10 to 20 with value 15 -> 50%
    row = analyzer.flag({"key": "urea", "name": "Blood Urea", "value": 27.5, "unit": "mg/dL", "ref_low": 15.0, "ref_high": 40.0, "category": "Kidney"})
    assert row["position_pct"] == 50.0

def test_unit_normalization_glucose():
    # Glucose reported in mmol/L (e.g. 5.5 mmol/L * 18.0182 = 99.1 mg/dL)
    row = {"key": "glucose_f", "name": "Fasting Glucose", "value": 5.5, "unit": "mmol/L", "ref_low": 3.9, "ref_high": 5.6, "category": "Diabetes"}
    res = analyzer.flag(row)
    assert res["unit"] == "mg/dL"
    assert res["value"] == 99.1
    assert res["status"] == "normal"
    assert res["original_value"] == 5.5
    assert res["original_unit"] == "mmol/L"

def test_unit_normalization_hemoglobin_gl():
    # Hemoglobin reported in g/L (e.g. 140 g/L -> 14.0 g/dL)
    row = {"key": "hemoglobin", "name": "Hemoglobin", "value": 140.0, "unit": "g/L", "ref_low": 130.0, "ref_high": 170.0, "category": "CBC"}
    res = analyzer.flag(row)
    assert res["unit"] == "g/dL"
    assert res["value"] == 14.0
    assert res["status"] == "normal"

def test_plausibility_bounds():
    # Impossible human hemoglobin value (e.g. 500 g/dL from OCR error)
    row = {"key": "hemoglobin", "name": "Hemoglobin", "value": 500.0, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "category": "CBC"}
    res = analyzer.flag(row)
    assert res["plausible"] is False
    assert "outside human physiological bounds" in res["plausibility_error"]

def test_critical_value_hyperkalemia():
    # Potassium 6.5 mmol/L (>= 6.2 is critical hyperkalemia)
    row = {"key": "potassium", "name": "Potassium", "value": 6.5, "unit": "mmol/L", "ref_low": 3.5, "ref_high": 5.1, "category": "Electrolytes"}
    res = analyzer.flag(row)
    assert res["is_critical"] is True
    assert res["severity"] == "marked"
    assert "Hyperkalemia" in res["critical_alert"]

def test_critical_value_hypoglycemia():
    # Fasting Glucose 45.0 mg/dL (<= 50 is critical hypoglycemia)
    row = {"key": "glucose_f", "name": "Fasting Glucose", "value": 45.0, "unit": "mg/dL", "ref_low": 70.0, "ref_high": 100.0, "category": "Diabetes"}
    res = analyzer.flag(row)
    assert res["is_critical"] is True
    assert res["status"] == "low"
    assert res["severity"] == "marked"
    assert "Hypoglycemia" in res["critical_alert"]

