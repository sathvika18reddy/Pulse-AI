"""
HL7 FHIR R4 Interoperability & RFC 5545 iCalendar Service:
- Standardized FHIR R4 Document / DiagnosticReport Bundle export (global EHR and ABHA/ABDM compatible).
- Direct structured FHIR R4 bundle ingestion (direct lab API connectivity bypassing OCR).
- RFC 5545 iCalendar reminder generation (.ics) for physician appointments with clinical talking points.
"""

import json, uuid, datetime
from pathlib import Path
import kb

def export_fhir_bundle(report: dict, patient_profile: dict = None) -> dict:
    """
    Export a laboratory report as an HL7 FHIR R4 Bundle.
    Includes Patient, Observation (with official LOINC codes & UCUM units), and DiagnosticReport resources.
    """
    bundle_id = str(uuid.uuid4())
    patient_id = f"pat-{report.get('session_id', 'default')[:8]}"
    doc_id = f"diag-{report.get('id', uuid.uuid4().hex[:8])}"
    
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    patient_resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "gender": (report.get("patient_sex") or "unknown").lower(),
    }
    if report.get("patient_age"):
        birth_year = datetime.datetime.utcnow().year - int(report["patient_age"])
        patient_resource["birthDate"] = f"{birth_year}-01-01"
        
    entries = [
        {
            "fullUrl": f"urn:uuid:{patient_id}",
            "resource": patient_resource
        }
    ]
    
    observation_refs = []
    
    for idx, row in enumerate(report.get("results", [])):
        obs_id = f"obs-{report.get('id', 'rep')}-{idx+1}"
        loinc = row.get("loinc") or kb.get_loinc(row.get("key", ""))
        
        # Interpretation code: N (Normal), L (Low), H (High), A (Abnormal)
        status = row.get("status", "normal")
        interp_code = "N"
        interp_display = "Normal"
        if status == "low":
            interp_code = "L"
            interp_display = "Low"
        elif status == "high":
            interp_code = "H"
            interp_display = "High"
        if row.get("is_critical"):
            interp_code = "CR"
            interp_display = "Critical"

        obs_resource = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                            "display": "Laboratory"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": loinc if loinc != "Unknown" else "11502-2",
                        "display": row.get("name")
                    }
                ],
                "text": row.get("name")
            },
            "subject": {"reference": f"urn:uuid:{patient_id}"},
            "valueQuantity": {
                "value": float(row.get("value", 0)),
                "unit": row.get("unit", ""),
                "system": "http://unitsofmeasure.org"
            },
            "interpretation": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": interp_code,
                            "display": interp_display
                        }
                    ]
                }
            ]
        }
        
        if row.get("ref_low") is not None or row.get("ref_high") is not None:
            ref_range = {}
            if row.get("ref_low") is not None:
                ref_range["low"] = {"value": float(row["ref_low"]), "unit": row.get("unit", "")}
            if row.get("ref_high") is not None:
                ref_range["high"] = {"value": float(row["ref_high"]), "unit": row.get("unit", "")}
            obs_resource["referenceRange"] = [ref_range]
            
        entries.append({
            "fullUrl": f"urn:uuid:{obs_id}",
            "resource": obs_resource
        })
        observation_refs.append({"reference": f"urn:uuid:{obs_id}"})
        
    diag_report = {
        "resourceType": "DiagnosticReport",
        "id": doc_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "LAB",
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "11502-2",
                    "display": "Laboratory report"
                }
            ],
            "text": "Pulse AI Laboratory Analysis Report"
        },
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "issued": timestamp,
        "result": observation_refs,
        "conclusion": report.get("summary", "")
    }
    
    entries.append({
        "fullUrl": f"urn:uuid:{doc_id}",
        "resource": diag_report
    })
    
    bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "document",
        "timestamp": timestamp,
        "entry": entries
    }
    return bundle

def import_fhir_bundle(bundle_json: dict) -> tuple[list[dict], dict]:
    """
    Ingest a standardized HL7 FHIR R4 Bundle directly.
    Bypasses OCR to parse structured digital lab partner feeds.
    Returns (rows, meta).
    """
    entries = bundle_json.get("entry", [])
    rows = []
    meta = {}
    
    # Map LOINC codes to internal keys
    loinc_to_key = {v: k for k, v in getattr(kb, "LOINC_CODES", {}).items() if v != "Unknown"}
    
    for entry in entries:
        res = entry.get("resource", {})
        rtype = res.get("resourceType")
        
        # Demographics from Patient
        if rtype == "Patient":
            if res.get("gender"):
                meta["sex"] = res["gender"].lower()
            if res.get("birthDate"):
                try:
                    byear = int(res["birthDate"].split("-")[0])
                    meta["age"] = datetime.datetime.utcnow().year - byear
                except Exception:
                    pass
                    
        # Date from DiagnosticReport
        elif rtype == "DiagnosticReport":
            if res.get("effectiveDateTime"):
                meta["date"] = res["effectiveDateTime"][:10]
            elif res.get("issued"):
                meta["date"] = res["issued"][:10]
                
        # Biomarkers from Observation
        elif rtype == "Observation":
            code_obj = res.get("code", {})
            codings = code_obj.get("coding", [])
            matched_key = None
            display_name = code_obj.get("text", "")
            
            for c in codings:
                loinc_code = c.get("code")
                if loinc_code in loinc_to_key:
                    matched_key = loinc_to_key[loinc_code]
                    break
                if not display_name and c.get("display"):
                    display_name = c.get("display")
                    
            if not matched_key and display_name:
                m = kb.find_marker(display_name)
                if m:
                    matched_key = m["key"]
                    
            if matched_key:
                val_qty = res.get("valueQuantity", {})
                val = val_qty.get("value")
                unit = val_qty.get("unit")
                
                rlo = None
                rhi = None
                rr = res.get("referenceRange", [])
                if rr and isinstance(rr, list):
                    low_obj = rr[0].get("low", {})
                    high_obj = rr[0].get("high", {})
                    if "value" in low_obj:
                        rlo = float(low_obj["value"])
                    if "value" in high_obj:
                        rhi = float(high_obj["value"])
                        
                m_info = kb.BY_KEY.get(matched_key, {})
                rows.append({
                    "key": matched_key,
                    "name": m_info.get("name", display_name),
                    "value": float(val) if val is not None else 0.0,
                    "unit": unit or m_info.get("unit", ""),
                    "ref_low": rlo,
                    "ref_high": rhi,
                    "category": m_info.get("category", "General"),
                    "ocr_confidence": 1.0,
                    "source": "fhir_direct"
                })
                
    return rows, meta

def generate_icalendar_reminder(report: dict, appointment_date: str = None, appointment_time: str = "10:00", doctor_name: str = "Dr. Clinical Specialist", notes: str = None) -> str:
    """
    Generate RFC 5545 compliant .ics calendar event file.
    Pre-populates appointment talking points and key out-of-range biomarkers.
    """
    now = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    uid = f"{report.get('id', 'pulse')}-{uuid.uuid4().hex[:6]}@pulseai.health"
    
    # Calculate appointment start and end times
    if appointment_date:
        try:
            parts = appointment_date.replace("/", "-").split("-")
            if len(parts[0]) == 4:  # YYYY-MM-DD
                dt_str = f"{parts[0]}{parts[1].zfill(2)}{parts[2].zfill(2)}"
            else:  # DD-MM-YYYY
                dt_str = f"{parts[2]}{parts[1].zfill(2)}{parts[0].zfill(2)}"
        except Exception:
            dt_str = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).strftime("%Y%m%d")
    else:
        dt_str = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).strftime("%Y%m%d")
        
    time_clean = appointment_time.replace(":", "") if appointment_time else "1000"
    if len(time_clean) == 4:
        time_clean += "00"
    dtstart = f"{dt_str}T{time_clean}"
    
    # End time 45 minutes later
    dt_obj = datetime.datetime.strptime(dtstart, "%Y%m%dT%H%M%S")
    dtend = (dt_obj + datetime.timedelta(minutes=45)).strftime("%Y%m%dT%H%M%S")
    
    # Extract out-of-range markers
    ab_markers = [f"- {r['name']}: {r['value']} {r['unit']} ({r['status'].upper()})" for r in report.get("results", []) if r.get("status") != "normal"]
    ab_text = "\\n".join(ab_markers) if ab_markers else "All routine markers were in normal range."
    
    summary_title = f"Medical Consultation: Review Blood Labs ({doctor_name})"
    
    description = (
        f"PULSE AI - CLINICAL APPOINTMENT BRIEF\\n\\n"
        f"Lab Report: {report.get('filename', 'Blood Report')}\\n"
        f"Date of Test: {report.get('date', 'Recent')}\\n\\n"
        f"KEY FINDINGS TO DISCUSS WITH PHYSICIAN:\\n"
        f"{ab_text}\\n\\n"
        f"SUGGESTED QUESTIONS TO ASK:\\n"
        f"1. What do these abnormal results mean in the context of my symptoms and family history?\\n"
        f"2. Do you recommend confirmatory follow-up tests or repeat blood work?\\n"
        f"3. Are any medication adjustments or targeted lifestyle steps indicated?\\n\\n"
        f"Notes: {notes or 'Bring printed Pulse AI Clinical Brief to consultation.'}"
    )
    
    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Pulse AI//Clinical Intelligence Platform//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{now}\r\n"
        f"DTSTART:{dtstart}\r\n"
        f"DTEND:{dtend}\r\n"
        f"SUMMARY:{summary_title}\r\n"
        f"DESCRIPTION:{description}\r\n"
        "LOCATION:Physician Clinic / Hospital\r\n"
        "STATUS:CONFIRMED\r\n"
        "BEGIN:VALARM\r\n"
        "TRIGGER:-PT24H\r\n"
        "ACTION:DISPLAY\r\n"
        "DESCRIPTION:Reminder: Doctor Appointment Tomorrow - Have Pulse AI lab summary ready\r\n"
        "END:VALARM\r\n"
        "BEGIN:VALARM\r\n"
        "TRIGGER:-PT2H\r\n"
        "ACTION:DISPLAY\r\n"
        "DESCRIPTION:Reminder: Doctor Appointment in 2 Hours\r\n"
        "END:VALARM\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    return ics_content
