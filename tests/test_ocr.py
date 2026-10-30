import pytest
import ocr

def test_parse_text_diverse_sample_lines():
    sample_text = """
    CITY LAB PATIENT REPORT
    Date: 12/03/2026
    1. Hemoglobin 10.8 g/dL 13.0 - 17.0
    2. Total Cholesterol 232 mg/dL < 200
    3. HDL Cholesterol 36 mg/dL 40 – 100
    4. Fasting Blood Sugar 118 mg/dL 70-100
    5. TSH 2.1 uIU/mL 0.4 to 4.5
    6. Vitamin D 18 ng/mL 30 - 100
    7. Platelet Count 255,000 /uL 150000 - 410000
    8. WBC Count 7200 /uL 4000 - 11000
    9. Serum Creatinine 1.2 mg/dL 0.7 - 1.3
    10. Potassium 4.2 mmol/L > 3.5
    """
    rows, meta = ocr.parse_text(sample_text)
    
    assert meta.get("date") == "12/03/2026"
    assert len(rows) == 10
    
    by_key = {r["key"]: r for r in rows}
    
    # Line 1: Standard hyphen range
    assert by_key["hemoglobin"]["value"] == 10.8
    assert by_key["hemoglobin"]["ref_low"] == 13.0
    assert by_key["hemoglobin"]["ref_high"] == 17.0
    assert by_key["hemoglobin"]["unit"] == "g/dL"
    assert by_key["hemoglobin"]["category"] == "CBC"
    
    # Line 2: Less than (< 200)
    assert by_key["chol"]["value"] == 232.0
    assert by_key["chol"]["ref_low"] == 0.0
    assert by_key["chol"]["ref_high"] == 200.0
    assert by_key["chol"]["category"] == "Lipid"
    
    # Line 3: En-dash range (40 – 100)
    assert by_key["hdl"]["value"] == 36.0
    assert by_key["hdl"]["ref_low"] == 40.0
    assert by_key["hdl"]["ref_high"] == 100.0
    
    # Line 4: Compact hyphen (70-100)
    assert by_key["glucose_f"]["value"] == 118.0
    assert by_key["glucose_f"]["ref_low"] == 70.0
    assert by_key["glucose_f"]["ref_high"] == 100.0
    assert by_key["glucose_f"]["category"] == "Diabetes"
    
    # Line 5: Word separator ("to")
    assert by_key["tsh"]["value"] == 2.1
    assert by_key["tsh"]["ref_low"] == 0.4
    assert by_key["tsh"]["ref_high"] == 4.5
    
    # Line 6: Standard range
    assert by_key["vitd"]["value"] == 18.0
    assert by_key["vitd"]["ref_low"] == 30.0
    assert by_key["vitd"]["ref_high"] == 100.0
    
    # Line 7: Comma in number (255,000)
    assert by_key["platelets"]["value"] == 255000.0
    assert by_key["platelets"]["ref_low"] == 150000.0
    assert by_key["platelets"]["ref_high"] == 410000.0
    
    # Line 8: Integer format
    assert by_key["wbc"]["value"] == 7200.0
    assert by_key["wbc"]["ref_low"] == 4000.0
    assert by_key["wbc"]["ref_high"] == 11000.0
    
    # Line 9: Kidney marker alias
    assert by_key["creatinine"]["value"] == 1.2
    assert by_key["creatinine"]["ref_low"] == 0.7
    assert by_key["creatinine"]["ref_high"] == 1.3
    
    # Line 10: Greater than (> 3.5)
    assert by_key["potassium"]["value"] == 4.2
    assert by_key["potassium"]["ref_low"] == 3.5
    assert by_key["potassium"]["ref_high"] is None

def test_parse_text_empty_and_noise():
    rows, meta = ocr.parse_text("Nothing to see here.\nJust a receipt 1234.56 USD")
    assert rows == []
    assert meta == {}

def test_parse_text_demographics_and_expanded_biomarkers():
    report_text = """
    METRO DIAGNOSTICS
    Patient Name: John Doe   Age: 48 Yrs   Gender: Male
    Date: 2026-10-15
    ESR 18 mm/hr 0 - 15
    eGFR 98 mL/min/1.73m2 90 - 120
    Serum Ferritin 42 ng/mL 24 - 336
    Total Bilirubin 0.8 mg/dL 0.1 - 1.2
    Direct Bilirubin 0.2 mg/dL 0.0 - 0.3
    Calcium 9.4 mg/dL 8.5 - 10.5
    """
    rows, meta = ocr.parse_text(report_text)
    assert meta.get("age") == 48
    assert meta.get("sex") == "male"
    assert meta.get("date") == "2026-10-15"

    by_key = {r["key"]: r for r in rows}
    assert by_key["esr"]["value"] == 18.0
    assert by_key["egfr"]["value"] == 98.0
    assert by_key["ferritin"]["value"] == 42.0
    assert by_key["bili"]["value"] == 0.8
    assert by_key["bili_dir"]["value"] == 0.2
    assert by_key["calcium"]["value"] == 9.4
