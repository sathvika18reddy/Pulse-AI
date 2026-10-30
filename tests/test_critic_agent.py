import pytest
import agent

def test_critic_auditor_grounded_vs_hallucinated():
    sample_report = {
        "results": [
            {"key": "hemoglobin", "name": "Hemoglobin", "value": 10.8, "unit": "g/dL", "ref_low": 13.0, "ref_high": 17.0, "status": "low"},
            {"key": "glucose_f", "name": "Fasting Glucose", "value": 118.0, "unit": "mg/dL", "ref_low": 70.0, "ref_high": 100.0, "status": "high"}
        ]
    }
    
    # 1. Perfectly grounded text citing only real report numbers
    good_text = "Your Hemoglobin is 10.8 g/dL which is below the lower reference of 13.0 g/dL. Fasting glucose was measured at 118.0 mg/dL."
    audit_good = agent.CriticAgent.audit_content(good_text, sample_report)
    assert audit_good["grounding_passed"] is True
    assert audit_good["audit_stamp"] == "CLINICAL_AUDIT_VERIFIED"
    assert len(audit_good["ungrounded_numbers"]) == 0
    
    # 2. Text containing hallucinated numbers not present anywhere in the report
    bad_text = "Your Hemoglobin was 10.8, but your Calcium was 88.5 and your potassium was 77.3."
    audit_bad = agent.CriticAgent.audit_content(bad_text, sample_report)
    assert audit_bad["grounding_passed"] is False
    assert audit_bad["audit_stamp"] == "CLINICAL_AUDIT_AMBER"
    assert "88.5" in audit_bad["ungrounded_numbers"]
    assert "77.3" in audit_bad["ungrounded_numbers"]

def test_critic_auditor_enforces_modesty():
    sample_report = {"results": []}
    prescriptive_text = "I diagnose you with severe anemia and I prescribe ferrous sulfate 300mg."
    audit = agent.CriticAgent.audit_content(prescriptive_text, sample_report)
    
    # Check that forbidden prescription phrasing was sanitized
    assert "i diagnose you with" not in audit["audited_text"].lower()
    assert "i prescribe" not in audit["audited_text"].lower()
    assert "cannot prescribe" in audit["audited_text"] or "cannot formulate" in audit["audited_text"]
