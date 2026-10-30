import pytest
import rag

def test_rag_retrieves_matching_marker():
    mock_report = {
        "id": "mock_report_1",
        "date": "12/03/2026",
        "results": [
            {
                "key": "hemoglobin",
                "name": "Hemoglobin",
                "value": 10.8,
                "unit": "g/dL",
                "status": "low",
                "severity": "moderate",
                "ref_low": 13.0,
                "ref_high": 17.0,
                "meaning": "Suggests anaemia (e.g. iron, B12 or folate deficiency, blood loss)."
            },
            {
                "key": "glucose_f",
                "name": "Fasting Glucose",
                "value": 118.0,
                "unit": "mg/dL",
                "status": "high",
                "severity": "moderate",
                "ref_low": 70.0,
                "ref_high": 100.0,
                "meaning": "100-125 is pre-diabetes range."
            }
        ]
    }
    
    # Query regarding hemoglobin / anemia
    hb_hits = rag.retrieve(mock_report, "Why is my hemoglobin low or what does it mean?", k=5)
    assert len(hb_hits) > 0
    keys = [h["key"] for h in hb_hits]
    assert "hemoglobin" in keys
    assert any("Hemoglobin" in h["text"] for h in hb_hits)

    # Query regarding blood sugar / glucose
    sugar_hits = rag.retrieve(mock_report, "What is my fasting glucose or blood sugar level?", k=5)
    assert len(sugar_hits) > 0
    keys = [h["key"] for h in sugar_hits]
    assert "glucose_f" in keys
    assert any("Fasting Glucose" in h["text"] or "glucose" in h["text"].lower() for h in sugar_hits)

def test_rag_structure():
    mock_report = {
        "id": "mock_report_2",
        "results": [
            {
                "key": "vitd",
                "name": "Vitamin D (25-OH)",
                "value": 18.0,
                "unit": "ng/mL",
                "status": "low",
                "severity": "marked",
                "ref_low": 30.0,
                "ref_high": 100.0,
                "meaning": "Linked to bone pain and weakness."
            }
        ]
    }
    hits = rag.retrieve(mock_report, "Vitamin D bone pain", k=3)
    assert len(hits) > 0
    hit = hits[0]
    assert "source" in hit
    assert "key" in hit
    assert "text" in hit
    assert hit["key"] == "vitd"
