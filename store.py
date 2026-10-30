"""JSON report store with session isolation and report lifecycle management."""
import json, time, uuid, os
from pathlib import Path

D = Path(__file__).parent / "data" / "reports"
D.mkdir(parents=True, exist_ok=True)
P_DIR = Path(__file__).parent / "data" / "profiles"
P_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_FILE = Path(__file__).parent / "data" / "feedback.jsonl"

def save(results, meta, filename, session_id=None, summary="", speech_script=""):
    rid = uuid.uuid4().hex[:10]
    rec = dict(
        id=rid,
        session_id=session_id or "default",
        filename=filename,
        uploaded=time.time(),
        date=meta.get("date"),
        patient_age=meta.get("age"),
        patient_sex=meta.get("sex"),
        patient_name=meta.get("patient_name"),
        summary=summary,
        speech_script=speech_script,
        results=results
    )
    (D / f"{rid}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec

def update_summary(rid, summary, speech_script=""):
    rec = get(rid)
    if rec:
        rec["summary"] = summary
        if speech_script:
            rec["speech_script"] = speech_script
        (D / f"{rid}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        return rec
    return None

def update_record(rid, **fields):
    rec = get(rid)
    if rec:
        rec.update(fields)
        (D / f"{rid}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
        return rec
    return None

def get(rid, session_id=None):
    p = D / f"{rid}.json"
    if not p.exists():
        return None
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
        if session_id and rec.get("session_id") and rec["session_id"] != session_id:
            return None
        return rec
    except Exception:
        return None

def delete(rid, session_id=None):
    rec = get(rid, session_id=session_id)
    if rec:
        p = D / f"{rid}.json"
        if p.exists():
            p.unlink()
            return True
    return False

def all_reports(session_id=None):
    recs = []
    for p in D.glob("*.json"):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
            if session_id and r.get("session_id") and r["session_id"] != session_id:
                continue
            recs.append(r)
        except Exception:
            continue
    return sorted(recs, key=lambda r: r.get("uploaded", 0))

def list_reports(session_id=None):
    reports = all_reports(session_id)
    out = []
    for r in reports:
        ab = sum(1 for x in r.get("results", []) if x.get("status") != "normal")
        out.append(dict(
            id=r["id"],
            filename=r.get("filename", "report"),
            date=r.get("date") or "Unknown date",
            uploaded=r.get("uploaded", 0),
            patient_age=r.get("patient_age"),
            patient_sex=r.get("patient_sex"),
            total_markers=len(r.get("results", [])),
            abnormal_count=ab
        ))
    return sorted(out, key=lambda x: -x["uploaded"])

def save_patient_profile(session_id: str, profile_data: dict) -> dict:
    """Save persistent patient demographics, medications, conditions, and pregnancy status."""
    sid = session_id or "default"
    p = P_DIR / f"{sid}.json"
    existing = get_patient_profile(sid)
    existing.update(profile_data)
    existing["session_id"] = sid
    existing["updated_at"] = time.time()
    p.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return existing

def get_patient_profile(session_id: str) -> dict:
    """Retrieve patient clinical profile for the current session."""
    sid = session_id or "default"
    p = P_DIR / f"{sid}.json"
    if not p.exists():
        return {
            "session_id": sid,
            "age": None,
            "sex": None,
            "medications": [],
            "conditions": [],
            "pregnancy_trimester": None,
            "smoking_status": "non_smoker",
            "family_history": []
        }
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"session_id": sid, "medications": [], "conditions": []}

def save_feedback(feedback_data: dict) -> bool:
    """Log clinician and patient feedback for continuous clinical audit."""
    try:
        record = dict(feedback_data)
        record["timestamp"] = time.time()
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return True
    except Exception:
        return False

def get_patient_timeline(session_id: str) -> list[dict]:
    """Retrieve chronologically ordered visits with merged biomarker trajectories."""
    return all_reports(session_id)

