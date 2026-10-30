import pytest
import agent
import translations

@pytest.fixture
def sample_report():
    return {
        "id": "rep_multi_1",
        "date": "15/04/2026",
        "results": [
            {
                "key": "hemoglobin",
                "name": "Hemoglobin",
                "value": 11.2,
                "unit": "g/dL",
                "status": "low",
                "severity": "mild",
                "ref_low": 13.0,
                "ref_high": 17.0,
                "meaning": "Suggests mild anemia."
            },
            {
                "key": "glucose_f",
                "name": "Fasting Glucose",
                "value": 122.0,
                "unit": "mg/dL",
                "status": "high",
                "severity": "moderate",
                "ref_low": 70.0,
                "ref_high": 100.0,
                "meaning": "Prediabetes range."
            },
            {
                "key": "chol",
                "name": "Total Cholesterol",
                "value": 215.0,
                "unit": "mg/dL",
                "status": "high",
                "severity": "mild",
                "ref_low": 125.0,
                "ref_high": 200.0,
                "meaning": "Borderline high."
            }
        ]
    }

def test_multilingual_summary_hindi(sample_report):
    summary = agent.summarize(sample_report, lang="hi")
    assert "The Big Picture" in summary or "समग्र स्वास्थ्य स्थिति" in summary
    assert "Areas to Watch" in summary or "ध्यान देने योग्य परिणाम" in summary
    assert "Hemoglobin" in summary or "हीमोग्लोबिन" in summary
    assert "डॉक्टर" in summary or "चिकित्सक" in summary

def test_multilingual_summary_tamil(sample_report):
    summary = agent.summarize(sample_report, lang="ta")
    assert "The Big Picture" in summary or "ஒட்டுமொத்த சுகாதார நிலை" in summary
    assert "Areas to Watch" in summary or "கவனிக்க வேண்டிய முடிவுகள்" in summary

def test_multilingual_speech_script(sample_report):
    speech_hi = agent.generate_speech_script(sample_report, lang="hi")
    assert "नमस्ते" in speech_hi
    assert "(" not in speech_hi
    assert ")" not in speech_hi

    speech_ta = agent.generate_speech_script(sample_report, lang="ta")
    assert "வணக்கம்" in speech_ta

def test_multilingual_chat_greetings(sample_report):
    resp_hi = agent.chat(sample_report, [], "नमस्ते", lang="hi")
    assert "पल्स एआई" in resp_hi or "सहायक" in resp_hi

    resp_ta = agent.chat(sample_report, [], "வணக்கம்", lang="ta")
    assert "பல்ஸ் ஏஐ" in resp_ta

def test_multilingual_suggestions(sample_report):
    chips_hi = agent.get_follow_up_suggestions(sample_report, "test", lang="hi")
    assert len(chips_hi) >= 2
    assert any("डॉक्टर" in c or "आहार" in c for c in chips_hi)
