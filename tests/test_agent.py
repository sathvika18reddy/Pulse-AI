import pytest
import agent

@pytest.fixture
def sample_report():
    return {
        "id": "test_rep_1",
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
            },
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
            },
            {
                "key": "wbc",
                "name": "WBC Count",
                "value": 7200.0,
                "unit": "/uL",
                "status": "normal",
                "severity": "none",
                "ref_low": 4000.0,
                "ref_high": 11000.0,
                "meaning": ""
            }
        ]
    }

def test_chat_greeting(sample_report):
    resp = agent.chat(sample_report, [], "Hello", lang="en")
    assert "Pulse AI" in resp
    assert "explain" in resp.lower()

def test_chat_abnormal_query(sample_report):
    resp = agent.chat(sample_report, [], "What is abnormal in my blood test?", lang="en")
    assert "Hemoglobin" in resp
    assert "Fasting Glucose" in resp
    assert "Vitamin D" in resp
    assert "10.8" in resp
    assert "consult" in resp.lower() or "physician" in resp.lower()

def test_chat_specific_marker_why_low(sample_report):
    resp = agent.chat(sample_report, [], "Why is my hemoglobin low?", lang="en")
    assert "Hemoglobin" in resp
    assert "10.8 g/dL" in resp
    assert "low" in resp.lower()
    assert "13.0" in resp
    assert "iron" in resp.lower() or "anaemia" in resp.lower()

def test_chat_dietary_advice(sample_report):
    resp = agent.chat(sample_report, [], "What foods should I eat to improve my hemoglobin?", lang="en")
    assert "iron" in resp.lower()
    assert "greens" in resp.lower() or "lentils" in resp.lower() or "dietary" in resp.lower()

def test_chat_normal_marker(sample_report):
    resp = agent.chat(sample_report, [], "How is my WBC count?", lang="en")
    assert "WBC Count" in resp
    assert "7200.0" in resp
    assert "normal" in resp.lower()

def test_chat_doctor_questions(sample_report):
    resp = agent.chat(sample_report, [], "What should I ask my doctor about these results?", lang="en")
    assert "Hemoglobin" in resp
    assert "doctor" in resp.lower()

def test_chat_panel_overview(sample_report):
    resp = agent.chat(sample_report, [], "How is my CBC panel?", lang="en")
    assert "Complete Blood Count" in resp

def test_redact_pii():
    text = "Patient John Doe, Phone: 555-123-4567, Email: john.doe@example.com, MRN: 9876543."
    clean = agent.redact_pii(text)
    assert "555-123-4567" not in clean
    assert "[REDACTED_PHONE]" in clean
    assert "john.doe@example.com" not in clean
    assert "[REDACTED_EMAIL]" in clean
    assert "9876543" not in clean
    assert "[REDACTED_ID]" in clean

def test_verify_grounding_safety_disclaimer(sample_report):
    hallucinated = "I prescribe 500mg of Metformin daily and diagnose you with Type 2 Diabetes."
    safe = agent.verify_grounding(hallucinated, sample_report)
    assert "cannot prescribe medications" in safe

def test_speech_script_conversational(sample_report):
    speech = agent.generate_speech_script(sample_report)
    assert "(" not in speech
    assert ")" not in speech
    assert "Hello" in speech
    assert "hemoglobin is a bit low" in speech.lower() or "hemoglobin" in speech.lower()

def test_follow_up_suggestions(sample_report):
    suggs = agent.get_follow_up_suggestions(sample_report, "Why is my hemoglobin low?")
    assert len(suggs) >= 2
    assert any("iron" in s.lower() or "doctor" in s.lower() for s in suggs)

