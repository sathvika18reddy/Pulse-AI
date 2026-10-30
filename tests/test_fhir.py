import pytest
import fhir, kb

def test_export_fhir_bundle():
    sample_report = {
        "id": "rep_test_123",
        "session_id": "sess_patient_45",
        "filename": "blood_panel.png",
        "date": "2026-10-15",
        "patient_sex": "male",
        "patient_age": 48,
        "summary": "Overall stable profile with mild lipid elevation.",
        "results": [
            {
                "key": "hemoglobin",
                "name": "Hemoglobin",
                "value": 14.2,
                "unit": "g/dL",
                "ref_low": 13.0,
                "ref_high": 17.0,
                "status": "normal",
                "severity": "none",
                "is_critical": False,
                "loinc": "718-7"
            },
            {
                "key": "glucose_f",
                "name": "Fasting Glucose",
                "value": 132.0,
                "unit": "mg/dL",
                "ref_low": 70.0,
                "ref_high": 100.0,
                "status": "high",
                "severity": "moderate",
                "is_critical": False,
                "loinc": "1558-6"
            }
        ]
    }
    
    bundle = fhir.export_fhir_bundle(sample_report)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "document"
    assert len(bundle["entry"]) == 4  # 1 Patient + 2 Observations + 1 DiagnosticReport
    
    # Check Patient resource
    pat_res = bundle["entry"][0]["resource"]
    assert pat_res["resourceType"] == "Patient"
    assert pat_res["gender"] == "male"
    assert "1978" in pat_res["birthDate"]
    
    # Check Observation resources
    obs_res_1 = bundle["entry"][1]["resource"]
    assert obs_res_1["resourceType"] == "Observation"
    assert obs_res_1["code"]["coding"][0]["code"] == "718-7"
    assert obs_res_1["valueQuantity"]["value"] == 14.2
    assert obs_res_1["interpretation"][0]["coding"][0]["code"] == "N"
    
    obs_res_2 = bundle["entry"][2]["resource"]
    assert obs_res_2["code"]["coding"][0]["code"] == "1558-6"
    assert obs_res_2["valueQuantity"]["value"] == 132.0
    assert obs_res_2["interpretation"][0]["coding"][0]["code"] == "H"
    
    # Check DiagnosticReport
    diag_res = bundle["entry"][3]["resource"]
    assert diag_res["resourceType"] == "DiagnosticReport"
    assert diag_res["status"] == "final"
    assert len(diag_res["result"]) == 2
    assert diag_res["conclusion"] == sample_report["summary"]

def test_import_fhir_bundle():
    fhir_bundle_input = {
        "resourceType": "Bundle",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "gender": "female",
                    "birthDate": "1990-05-12"
                }
            },
            {
                "resource": {
                    "resourceType": "DiagnosticReport",
                    "effectiveDateTime": "2026-10-20T08:30:00Z"
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "code": {
                        "coding": [{"system": "http://loinc.org", "code": "718-7", "display": "Hemoglobin"}]
                    },
                    "valueQuantity": {"value": 11.4, "unit": "g/dL"},
                    "referenceRange": [{"low": {"value": 12.0}, "high": {"value": 15.5}}]
                }
            },
            {
                "resource": {
                    "resourceType": "Observation",
                    "code": {
                        "coding": [{"system": "http://loinc.org", "code": "4548-4", "display": "HbA1c"}]
                    },
                    "valueQuantity": {"value": 6.8, "unit": "%"},
                    "referenceRange": [{"low": {"value": 4.0}, "high": {"value": 5.6}}]
                }
            }
        ]
    }
    
    rows, meta = fhir.import_fhir_bundle(fhir_bundle_input)
    assert meta.get("sex") == "female"
    assert meta.get("age") == 36
    assert meta.get("date") == "2026-10-20"
    assert len(rows) == 2
    
    hb = next(r for r in rows if r["key"] == "hemoglobin")
    assert hb["value"] == 11.4
    assert hb["ref_low"] == 12.0
    assert hb["ref_high"] == 15.5
    
    hba1c = next(r for r in rows if r["key"] == "hba1c")
    assert hba1c["value"] == 6.8
