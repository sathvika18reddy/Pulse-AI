import agent


def test_generate_ehr_soap_note_uses_expected_icd_codes():
    report = {
        "date": "2026-10-28",
        "patient_age": 52,
        "patient_sex": "male",
        "medications": ["Metformin 500mg"],
        "results": [
            {"key": "hba1c", "name": "HbA1c", "value": 6.8, "unit": "%", "status": "high", "ref_low": 4.0, "ref_high": 5.6},
            {"key": "glucose_f", "name": "Fasting Glucose", "value": 122, "unit": "mg/dL", "status": "high", "ref_low": 70, "ref_high": 99},
            {"key": "b12", "name": "Vitamin B12", "value": 175, "unit": "pg/mL", "status": "low", "ref_low": 200, "ref_high": 900},
            {"key": "alt", "name": "ALT", "value": 54, "unit": "U/L", "status": "high", "ref_low": 7, "ref_high": 40},
        ],
    }

    note = agent.generate_ehr_soap_note(report, profile={"medications": ["Metformin 500mg"]})

    assert "formatted_progress_note" in note
    codes = {entry["icd10_code"] for entry in note["billing_codes"]}
    assert "E11.69" in codes
    assert "E53.8" in codes
    assert "T38.3X5A" in codes
    assert "R74.01" in codes
