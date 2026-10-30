import pytest
import analyzer

def test_timeline_trajectory_and_velocity():
    # 2 reports for the same patient: 6 months apart
    history = [
        {
            "id": "rep1",
            "date": "2026-04-10",
            "uploaded": 1712707200,
            "results": [
                {"key": "hemoglobin", "name": "Hemoglobin", "value": 13.5, "unit": "g/dL", "status": "normal"},
                {"key": "glucose_f", "name": "Fasting Glucose", "value": 92.0, "unit": "mg/dL", "status": "normal"},
                {"key": "egfr", "name": "eGFR", "value": 85.0, "unit": "mL/min/1.73m2", "status": "normal"}
            ]
        },
        {
            "id": "rep2",
            "date": "2026-10-10",
            "uploaded": 1728518400,
            "results": [
                {"key": "hemoglobin", "name": "Hemoglobin", "value": 11.2, "unit": "g/dL", "status": "low"},
                {"key": "glucose_f", "name": "Fasting Glucose", "value": 118.0, "unit": "mg/dL", "status": "high"},
                {"key": "egfr", "name": "eGFR", "value": 72.0, "unit": "mL/min/1.73m2", "status": "normal"}
            ]
        }
    ]
    
    analysis = analyzer.analyze_trajectory(history)
    trajs = analysis["trajectories"]
    alerts = analysis["velocity_alerts"]
    
    assert "hemoglobin" in trajs
    assert trajs["hemoglobin"]["delta"] == -2.3
    assert trajs["hemoglobin"]["pct_change"] == -17.0
    assert trajs["hemoglobin"]["direction"] == "falling"
    
    assert "glucose_f" in trajs
    assert trajs["glucose_f"]["delta"] == 26.0
    assert trajs["glucose_f"]["pct_change"] == 28.3
    assert trajs["glucose_f"]["direction"] == "rising"
    
    # Rapid renal decline alert (85 -> 72 = 13 drop in ~6 months, exceeds 5/yr)
    renal_alert = next((a for a in alerts if a["alert_type"] == "rapid_renal_decline"), None)
    assert renal_alert is not None
    assert "Rapid eGFR Renal Decline" in renal_alert["title"]
    assert "KDIGO" in renal_alert["guideline"]
    
    # Progressive anemia alert (drop > 15%)
    anemia_alert = next((a for a in alerts if a["alert_type"] == "progressive_anemia"), None)
    assert anemia_alert is not None
    assert "Hemoglobin" in anemia_alert["name"]
