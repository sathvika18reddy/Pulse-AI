import pytest
import fhir

def test_icalendar_generation():
    sample_report = {
        "id": "cal_test_88",
        "filename": "annual_checkup.pdf",
        "date": "2026-10-18",
        "results": [
            {"key": "hemoglobin", "name": "Hemoglobin", "value": 10.4, "unit": "g/dL", "status": "low", "severity": "moderate", "is_critical": False},
            {"key": "chol", "name": "Total Cholesterol", "value": 242.0, "unit": "mg/dL", "status": "high", "severity": "moderate", "is_critical": False}
        ]
    }
    
    ics = fhir.generate_icalendar_reminder(
        sample_report,
        appointment_date="2026-11-05",
        appointment_time="14:30",
        doctor_name="Dr. Sarah Jenkins",
        notes="Discuss starting iron supplementation and statin therapy."
    )
    
    assert "BEGIN:VCALENDAR" in ics
    assert "VERSION:2.0" in ics
    assert "BEGIN:VEVENT" in ics
    assert "SUMMARY:Medical Consultation: Review Blood Labs (Dr. Sarah Jenkins)" in ics
    assert "DTSTART:20261105T143000" in ics
    assert "DTEND:20261105T151500" in ics
    assert "Hemoglobin: 10.4 g/dL (LOW)" in ics
    assert "Total Cholesterol: 242.0 mg/dL (HIGH)" in ics
    assert "BEGIN:VALARM" in ics
    assert "TRIGGER:-PT24H" in ics
    assert "END:VCALENDAR" in ics
