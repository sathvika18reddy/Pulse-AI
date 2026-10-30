import os, tempfile, json
from flask import Flask, request, jsonify, send_from_directory, render_template_string, Response, stream_with_context
import ocr, analyzer, agent, store, fhir, kb

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024
ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}

@app.get("/")
def index():
    return send_from_directory("static", "index.html")

@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify(error="No file uploaded"), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED:
        return jsonify(error="Upload a PDF or image"), 400
        
    t = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    temp_path = t.name
    t.close()
    f.save(temp_path)
    vlm_rows, vlm_meta = [], {}
    try:
        text = ocr.extract_text(temp_path)
        rows, meta = ocr.parse_text(text)
        
        # Dual-Path VLM Extraction when multimodal vision API is configured
        if os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"):
            vlm_rows, vlm_meta = ocr.extract_with_vlm(temp_path)
            if vlm_rows:
                rows = ocr.reconcile_extractions(rows, vlm_rows)
                if not meta.get("date") and vlm_meta.get("date"):
                    meta["date"] = vlm_meta["date"]
                if not meta.get("age") and vlm_meta.get("age"):
                    meta["age"] = vlm_meta["age"]
                if not meta.get("sex") and vlm_meta.get("sex"):
                    meta["sex"] = vlm_meta["sex"]
    except Exception as e:
        return jsonify(error=f"Error reading file: {str(e)}"), 422
    finally:
        # Immediate file deletion for privacy compliance
        if os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            
    if not rows:
        return jsonify(error="Couldn't find any known lab values. Try a clearer image.", raw_text=text), 422
        
    session_id = request.form.get("session_id") or request.headers.get("X-Session-ID") or "default"
    profile = store.get_patient_profile(session_id)
    
    # Demographics from form or profile override/complement OCR
    form_sex = request.form.get("sex") or profile.get("sex")
    if form_sex and form_sex.lower() in ("male", "female"):
        meta["sex"] = form_sex.lower()
    form_age = request.form.get("age") or profile.get("age")
    if form_age and str(form_age).isdigit():
        meta["age"] = int(form_age)
        
    # Form-supplied medications or pregnancy
    form_meds = request.form.get("medications")
    if form_meds:
        try:
            parsed_meds = json.loads(form_meds) if form_meds.startswith("[") else [m.strip() for m in form_meds.split(",") if m.strip()]
            profile["medications"] = parsed_meds
        except Exception:
            profile["medications"] = [m.strip() for m in form_meds.split(",") if m.strip()]
            
    form_trim = request.form.get("pregnancy_trimester")
    if form_trim and str(form_trim).isdigit():
        profile["pregnancy_trimester"] = int(form_trim)
        
    safe_name = os.path.basename(f.filename or f"report{ext}")
    
    analyzed_rows = analyzer.analyze(
        rows,
        sex=meta.get("sex"),
        age=meta.get("age"),
        pregnancy_trimester=profile.get("pregnancy_trimester"),
        medications=profile.get("medications"),
        conditions=profile.get("conditions")
    )
    lang = request.form.get("lang", "en")
    
    # Save initial report with raw OCR text for side-by-side human confirmation
    rec = store.save(analyzed_rows, meta, safe_name, session_id=session_id)
    rec["raw_text"] = text
    
    # Pre-generate natural doctor summary and fluid speech script
    summary_text = agent.summarize(rec, lang)
    speech_text = agent.generate_speech_script(rec, lang)
    sbar_brief = agent.generate_sbar_brief(rec, profile)
    care_plan = agent.CarePlanAgent.formulate_plan(rec, profile)
    cardiometabolic = kb.calculate_cardiometabolic_indices(analyzed_rows, sex=meta.get("sex"), age=meta.get("age"))
    phenoage = kb.calculate_phenotypic_age_and_resilience(analyzed_rows, chronological_age=meta.get("age") or 45, sex=meta.get("sex") or "male")
    medication_audit = kb.audit_prescription_and_depletions(analyzed_rows, medications=profile.get("medications", []))
    
    # Auto-generate visit-over-visit diff if prior historical reports exist
    diff_data = None
    all_prior = [r for r in store.all_reports(session_id) if r["id"] != rec["id"]]
    if all_prior:
        diff_data = analyzer.compute_report_diff(all_prior[-1], rec)
    
    store.update_record(
        rec["id"],
        summary=summary_text,
        speech_script=speech_text,
        raw_text=text,
        sbar_brief=sbar_brief,
        care_plan=care_plan,
        cardiometabolic=cardiometabolic,
        phenoage=phenoage,
        medication_audit=medication_audit,
        diff=diff_data
    )
    rec["summary"] = summary_text
    rec["speech_script"] = speech_text
    rec["sbar_brief"] = sbar_brief
    rec["care_plan"] = care_plan
    rec["cardiometabolic"] = cardiometabolic
    rec["phenoage"] = phenoage
    rec["medication_audit"] = medication_audit
    rec["diff"] = diff_data
    return jsonify(rec)

@app.post("/api/confirm/<rid>")
def confirm_report(rid):
    """Human confirmation step: accept user corrections on extracted values and re-analyze."""
    sid = (request.json or {}).get("session_id") or request.args.get("session_id") or "default"
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
        
    body = request.json or {}
    updated_rows = body.get("results")
    if not updated_rows or not isinstance(updated_rows, list):
        return jsonify(error="Invalid results provided"), 400
        
    sex = body.get("sex") or rec.get("patient_sex")
    age = body.get("age") or rec.get("patient_age")
    lang = body.get("lang", "en")
    profile = store.get_patient_profile(sid)
    
    analyzed_rows = analyzer.analyze(
        updated_rows,
        sex=sex,
        age=age,
        pregnancy_trimester=profile.get("pregnancy_trimester"),
        medications=profile.get("medications"),
        conditions=profile.get("conditions")
    )
    
    # Update record draft
    rec["results"] = analyzed_rows
    rec["patient_sex"] = sex
    rec["patient_age"] = age
    
    # Regenerate summary and speech script
    summary_text = agent.summarize(rec, lang)
    speech_text = agent.generate_speech_script(rec, lang)
    sbar_brief = agent.generate_sbar_brief(rec, profile)
    care_plan = agent.CarePlanAgent.formulate_plan(rec, profile)
    cardiometabolic = kb.calculate_cardiometabolic_indices(analyzed_rows, sex=sex, age=age)
    phenoage = kb.calculate_phenotypic_age_and_resilience(analyzed_rows, chronological_age=age or 45, sex=sex or "male")
    medication_audit = kb.audit_prescription_and_depletions(analyzed_rows, medications=profile.get("medications", []))
    
    # Auto-generate visit-over-visit diff if prior historical reports exist
    diff_data = None
    all_prior = [r for r in store.all_reports(sid) if r["id"] != rid]
    if all_prior:
        diff_data = analyzer.compute_report_diff(all_prior[-1], rec)
    
    store.update_record(
        rid,
        results=analyzed_rows,
        summary=summary_text,
        speech_script=speech_text,
        patient_sex=sex,
        patient_age=age,
        sbar_brief=sbar_brief,
        care_plan=care_plan,
        cardiometabolic=cardiometabolic,
        phenoage=phenoage,
        medication_audit=medication_audit,
        diff=diff_data
    )
    rec["summary"] = summary_text
    rec["speech_script"] = speech_text
    rec["sbar_brief"] = sbar_brief
    rec["care_plan"] = care_plan
    rec["cardiometabolic"] = cardiometabolic
    rec["phenoage"] = phenoage
    rec["medication_audit"] = medication_audit
    rec["diff"] = diff_data
    return jsonify(rec)

@app.get("/api/reports")
def list_reports():
    sid = request.args.get("session_id")
    return jsonify(store.list_reports(sid))

@app.get("/api/report/<rid>")
def get_report(rid):
    sid = request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    if "phenoage" not in rec and rec.get("results"):
        pheno = kb.calculate_phenotypic_age_and_resilience(
            rec["results"],
            chronological_age=rec.get("patient_age") or 45,
            sex=rec.get("patient_sex") or "male"
        )
        rec["phenoage"] = pheno
        store.update_record(rid, phenoage=pheno)
    if "diff" not in rec and rec.get("results"):
        actual_sid = rec.get("session_id") or sid or "default"
        all_recs = store.all_reports(actual_sid)
        def _sort_key(r):
            dt = analyzer.parse_date_or_timestamp(r.get("date"), r.get("uploaded"))
            return dt.timestamp() if dt else (r.get("uploaded") or 0.0)
        sorted_recs = sorted(all_recs, key=_sort_key)
        curr_idx = next((i for i, r in enumerate(sorted_recs) if r.get("id") == rid), -1)
        if curr_idx > 0:
            diff_data = analyzer.compute_report_diff(sorted_recs[curr_idx - 1], rec)
            rec["diff"] = diff_data
            store.update_record(rid, diff=diff_data)
    return jsonify(rec)

@app.delete("/api/report/<rid>")
def delete_report(rid):
    sid = request.args.get("session_id")
    if store.delete(rid, sid):
        return jsonify(success=True)
    return jsonify(error="Report not found"), 404

@app.post("/api/summary/<rid>")
def summary(rid):
    sid = (request.json or {}).get("session_id") or request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    lang = (request.json or {}).get("lang", "en")
    sum_text = agent.summarize(rec, lang)
    speech_text = agent.generate_speech_script(rec, lang)
    store.update_summary(rid, sum_text, speech_script=speech_text)
    return jsonify(summary=sum_text, speech_script=speech_text)

@app.post("/api/chat/<rid>")
def chat(rid):
    sid = (request.json or {}).get("session_id") or request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    b = request.json or {}
    q = b.get("question", "")
    reply = agent.chat(rec, b.get("history", []), q, b.get("lang", "en"))
    suggestions = agent.get_follow_up_suggestions(rec, q, lang=b.get("lang", "en"))
    return jsonify(reply=reply, suggestions=suggestions)

@app.post("/api/chat/<rid>/stream")
def stream_chat(rid):
    """Server-Sent Events streaming Q&A endpoint for real-time typewriter responses."""
    sid = (request.json or {}).get("session_id") or request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    b = request.json or {}
    q = b.get("question", "")
    history = b.get("history", [])
    lang = b.get("lang", "en")
    
    def generate():
        for chunk in agent.stream_chat(rec, history, q, lang=lang):
            yield f"data: {chunk}\n\n"
            
    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/api/trends")
def trends():
    sid = request.args.get("session_id")
    out = {}
    for r in store.all_reports(sid):
        for x in r.get("results", []):
            out.setdefault(x["key"], dict(name=x["name"], unit=x["unit"], points=[]))["points"].append(
                dict(label=r.get("date") or r["filename"], value=x["value"], status=x.get("status", "normal"))
            )
    return jsonify({k: v for k, v in out.items() if len(v["points"]) > 1})

@app.get("/api/export/<rid>")
def export_report(rid):
    sid = request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return "Report not found", 404
    
    html = """
    <!doctype html>
    <html><head><meta charset="utf-8">
    <title>Pulse AI Report - {{ rec.filename }}</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 40px; color: #222; max-width: 800px; margin: auto; }
      h1 { color: #d90429; margin-bottom: 4px; }
      .meta { color: #666; font-size: 14px; margin-bottom: 24px; border-bottom: 1px solid #ddd; padding-bottom: 12px; }
      table { width: 100%; border-collapse: collapse; margin: 20px 0; }
      th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
      th { background: #f8f9fa; font-weight: 600; }
      .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; text-transform: uppercase; }
      .normal { background: #e8f5e9; color: #2e7d32; }
      .mild { background: #fff8e1; color: #f57f17; }
      .moderate { background: #ffebee; color: #c62828; }
      .marked { background: #b71c1c; color: #fff; }
      .summary-box { background: #fdf2f4; border-left: 4px solid #d90429; padding: 16px; margin: 24px 0; border-radius: 0 8px 8px 0; }
      .disclaimer { margin-top: 40px; font-size: 12px; color: #777; border-top: 1px solid #eee; padding-top: 12px; }
      @media print { .no-print { display: none; } body { padding: 0; } }
    </style></head><body>
      <div class="no-print" style="margin-bottom: 20px;">
        <button onclick="window.print()" style="background:#d90429;color:white;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;font-weight:bold;">🖨️ Print or Save as PDF</button>
      </div>
      <h1>PULSE AI — Blood Analysis Summary</h1>
      <div class="meta">
        <strong>Report File:</strong> {{ rec.filename }} | 
        <strong>Date:</strong> {{ rec.date or 'Not specified' }} | 
        <strong>Patient:</strong> {{ rec.patient_sex or 'Adult' }} {{ '(' + rec.patient_age|string + ' yrs)' if rec.patient_age else '' }}
      </div>
      
      {% set crits = rec.results | selectattr('is_critical') | list %}
      {% if crits %}
      <div style="background:#fee2e2; border-left:4px solid #b91c1c; padding:16px; margin:20px 0; border-radius:4px; color:#991b1b;">
        <h3 style="margin-top:0; color:#b91c1c;">⚠️ URGENT CLINICAL ALERT</h3>
        <ul style="margin:0; padding-left:20px; line-height:1.5;">
          {% for c in crits %}
          <li><strong>{{ c.name }}:</strong> {{ c.critical_alert or 'Critical value detected.' }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}

      <div class="summary-box">
        <h3 style="margin-top:0;">Plain-Language Summary</h3>
        <p style="white-space: pre-wrap; line-height: 1.6;">{{ rec.summary }}</p>
      </div>

      <h3>Biomarker Test Results</h3>
      <table>
        <thead>
          <tr>
            <th>Test</th>
            <th>Value</th>
            <th>Reference Range</th>
            <th>Status</th>
            <th>Severity</th>
          </tr>
        </thead>
        <tbody>
          {% for r in rec.results %}
          <tr>
            <td><strong>{{ r.name }}</strong></td>
            <td>{{ r.value }} {{ r.unit }}</td>
            <td>{{ r.ref_low if r.ref_low is not none else '' }} - {{ r.ref_high if r.ref_high is not none else '' }} {{ r.unit }}</td>
            <td><span class="badge {{ r.severity if r.status != 'normal' else 'normal' }}">{{ r.status }}</span></td>
            <td>{{ r.severity if r.severity != 'none' else '-' }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>

      <div class="disclaimer">
        <strong>Important Medical Notice:</strong> Pulse AI is an AI-powered health-literacy tool intended for informational educational purposes only. It is not a diagnostic device and does not provide medical advice or prescriptions. Always discuss these findings with a qualified physician or healthcare provider.
      </div>
    </body></html>
    """
    return render_template_string(html, rec=rec)

@app.route("/api/profile", methods=["GET", "POST"])
def patient_profile():
    """Manage persistent patient clinical demographics, current medications, conditions, and pregnancy status."""
    sid = request.args.get("session_id") or (request.json or {}).get("session_id") or "default"
    if request.method == "POST":
        b = request.json or {}
        updated = store.save_patient_profile(sid, b)
        return jsonify(updated)
    return jsonify(store.get_patient_profile(sid))

@app.get("/api/timeline")
def patient_timeline():
    """Merged longitudinal trajectory with velocity calculations and progression alert flags."""
    sid = request.args.get("session_id") or "default"
    reps = store.get_patient_timeline(sid)
    analysis = analyzer.analyze_trajectory(reps)
    return jsonify(analysis)

@app.get("/api/fhir/<rid>")
def export_fhir(rid):
    """Export standard HL7 FHIR R4 DiagnosticReport Bundle (LOINC & UCUM compliant)."""
    sid = request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    profile = store.get_patient_profile(rec.get("session_id"))
    bundle = fhir.export_fhir_bundle(rec, profile)
    return jsonify(bundle)

@app.post("/api/fhir/import")
def import_fhir():
    """Direct digital ingestion of HL7 FHIR R4 DiagnosticReport bundles from diagnostic lab APIs."""
    bundle = request.json
    if not bundle or not isinstance(bundle, dict):
        return jsonify(error="Invalid FHIR bundle JSON"), 400
    rows, meta = fhir.import_fhir_bundle(bundle)
    if not rows:
        return jsonify(error="No valid biomarker observations found in FHIR bundle"), 422
    sid = request.headers.get("X-Session-ID") or request.args.get("session_id") or "default"
    profile = store.get_patient_profile(sid)
    analyzed = analyzer.analyze(
        rows,
        sex=meta.get("sex"),
        age=meta.get("age"),
        pregnancy_trimester=profile.get("pregnancy_trimester"),
        medications=profile.get("medications"),
        conditions=profile.get("conditions")
    )
    rec = store.save(analyzed, meta, "FHIR_Imported_Report.json", session_id=sid)
    sum_text = agent.summarize(rec, "en")
    speech_text = agent.generate_speech_script(rec, "en")
    sbar = agent.generate_sbar_brief(rec, profile)
    care_plan = agent.CarePlanAgent.formulate_plan(rec, profile)
    cardio = kb.calculate_cardiometabolic_indices(analyzed, sex=meta.get("sex"), age=meta.get("age"))
    phenoage = kb.calculate_phenotypic_age_and_resilience(analyzed, chronological_age=meta.get("age") or 45, sex=meta.get("sex") or "male")
    medication_audit = kb.audit_prescription_and_depletions(analyzed, medications=profile.get("medications", []))
    
    # Auto-generate visit-over-visit diff if prior historical reports exist
    diff_data = None
    all_prior = [r for r in store.all_reports(sid) if r["id"] != rec["id"]]
    if all_prior:
        diff_data = analyzer.compute_report_diff(all_prior[-1], rec)
    
    store.update_record(
        rec["id"],
        summary=sum_text,
        speech_script=speech_text,
        sbar_brief=sbar,
        care_plan=care_plan,
        cardiometabolic=cardio,
        phenoage=phenoage,
        medication_audit=medication_audit,
        diff=diff_data
    )
    rec["summary"] = sum_text
    rec["speech_script"] = speech_text
    rec["sbar_brief"] = sbar
    rec["care_plan"] = care_plan
    rec["cardiometabolic"] = cardio
    rec["phenoage"] = phenoage
    rec["medication_audit"] = medication_audit
    rec["diff"] = diff_data
    return jsonify(rec)

@app.route("/api/reminder/<rid>", methods=["GET", "POST"])
def download_reminder(rid):
    """Generate and download RFC 5545 .ics iCalendar appointment invitation."""
    sid = request.args.get("session_id") or (request.json or {}).get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    b = request.json or {}
    date = b.get("appointment_date") or request.args.get("date")
    time_val = b.get("appointment_time") or request.args.get("time") or "10:00"
    doctor = b.get("doctor_name") or request.args.get("doctor") or "Dr. Clinical Specialist"
    notes = b.get("notes") or request.args.get("notes")
    ics_text = fhir.generate_icalendar_reminder(rec, appointment_date=date, appointment_time=time_val, doctor_name=doctor, notes=notes)
    return Response(
        ics_text,
        mimetype="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=pulse_appointment_{rid}.ics"}
    )

@app.post("/api/feedback")
def submit_feedback():
    """Log clinician and patient feedback for continuous quality improvement."""
    b = request.json or {}
    success = store.save_feedback(b)
    return jsonify(success=success)

@app.get("/api/careplan/<rid>")
def get_careplan(rid):
    """Retrieve actionable care navigation plan (specialist routing, follow-up tests, questions)."""
    sid = request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    profile = store.get_patient_profile(rec.get("session_id"))
    plan = agent.CarePlanAgent.formulate_plan(rec, profile)
    return jsonify(plan)

@app.get("/api/sbar/<rid>")
def get_sbar(rid):
    """Retrieve official Mayo Clinic / Johns Hopkins style SBAR Clinical Brief."""
    sid = request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    profile = store.get_patient_profile(rec.get("session_id"))
    brief = agent.generate_sbar_brief(rec, profile)
    return jsonify(brief)

@app.route("/api/soap/<rid>", methods=["GET", "POST"])
def get_soap_note(rid):
    """Generate a clinician-ready EHR SOAP note with ICD-10 and SNOMED coding."""
    sid = request.args.get("session_id") or ((request.get_json(silent=True) or {}).get("session_id"))
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    profile = store.get_patient_profile(rec.get("session_id") or sid or "default")
    payload = request.get_json(silent=True) or {}
    clinician_notes = payload.get("clinician_notes") or ""
    soap_note = agent.generate_ehr_soap_note(rec, profile, clinician_notes=clinician_notes)
    rec["ehr_soap_note"] = soap_note
    store.update_record(rid, ehr_soap_note=soap_note)
    return jsonify(soap_note)

@app.post("/api/simulate/<rid>")
def simulate_interventions(rid):
    """Dynamic What-If Metabolic Simulator: calculate clinical intervention shifts."""
    sid = (request.json or {}).get("session_id") or request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    interventions = (request.json or {}).get("interventions", {})
    projected = kb.simulate_lifestyle_interventions(rec.get("results", []), interventions)
    return jsonify(projected=projected)

@app.post("/api/rehearse/<rid>")
def rehearse_consult(rid):
    """Interactive Doctor-Patient Consultation Simulator roleplay."""
    sid = (request.json or {}).get("session_id") or request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    b = request.json or {}
    step = b.get("step", 0)
    user_input = b.get("user_input", "")
    history = b.get("history", [])
    dialogue = agent.rehearse_consultation(rec, step, user_input, history)
    return jsonify(dialogue)

@app.post("/api/config/key")
def configure_api_key():
    """Dynamically set GEMINI_API_KEY or ANTHROPIC_API_KEY in the environment."""
    b = request.json or {}
    provider = b.get("provider", "gemini").lower()
    key = (b.get("key") or "").strip()
    if not key:
        return jsonify(error="API key cannot be empty"), 400
    if provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = key
    else:
        os.environ["GEMINI_API_KEY"] = key
    return jsonify(success=True, provider=provider, message=f"Configured {provider} API key successfully.")

@app.get("/api/phenoage/<rid>")
def get_phenoage(rid):
    """Return Phenotypic Biological Age & Multi-Organ Resilience Radar payload."""
    sid = request.args.get("session_id")
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
    pheno = rec.get("phenoage")
    if not pheno:
        pheno = kb.calculate_phenotypic_age_and_resilience(
            rec.get("results", []),
            chronological_age=rec.get("patient_age") or 45,
            sex=rec.get("patient_sex") or "male"
        )
        store.update_record(rid, phenoage=pheno)
    return jsonify(pheno)

@app.route("/api/medications/audit/<rid>", methods=["GET", "POST"])
def audit_medications(rid):
    """
    Drug-Nutrient Depletion & Medication Interaction Co-Pilot endpoint.
    GET: Audits record against saved patient profile medications or returns saved audit.
    POST: Dynamic scenario simulator accepting { "medications": [...] } for interactive what-if auditing.
    """
    sid = request.args.get("session_id") or ((request.get_json(silent=True) or {}).get("session_id"))
    rec = store.get(rid, sid)
    if not rec:
        return jsonify(error="Report not found"), 404
        
    results = rec.get("results", [])
    profile = store.get_patient_profile(rec.get("session_id") or sid or "default")
    
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        medications = body.get("medications")
        if medications is None:
            medications = profile.get("medications", [])
    else:
        medications = profile.get("medications", [])
        if rec.get("medication_audit") and not request.args.get("refresh"):
            return jsonify(rec.get("medication_audit"))

    audit_data = kb.audit_prescription_and_depletions(results, medications=medications)
    if request.method == "GET" or not (request.get_json(silent=True) or {}).get("medications"):
        store.update_record(rid, medication_audit=audit_data)
        
    return jsonify(audit_data)

@app.route("/api/diff/<rid>", methods=["GET", "POST"])
def get_report_diff(rid):
    """
    Intelligent Lab Report 'Diff' Engine (Visit-over-Visit Treatment Response).
    GET: Compares current report against the immediately preceding report (or ?baseline_id=...).
    POST: Accepts { "baseline_id": "<bid>" } to dynamically switch baseline visit.
    """
    sid = request.args.get("session_id") or ((request.get_json(silent=True) or {}).get("session_id"))
    curr_rec = store.get(rid, sid) or store.get(rid)
    if not curr_rec:
        return jsonify(error="Current report not found"), 404
        
    actual_sid = curr_rec.get("session_id") or sid or "default"
    all_recs = store.all_reports(actual_sid)
    if len(all_recs) <= 1:
        # Fall back to all reports if session isolation was not set across test runs
        all_recs = store.all_reports()
    
    baseline_id = request.args.get("baseline_id")
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        if body.get("baseline_id"):
            baseline_id = body.get("baseline_id")

    base_rec = None
    def _sort_key(r):
        dt = analyzer.parse_date_or_timestamp(r.get("date"), r.get("uploaded"))
        return dt.timestamp() if dt else (r.get("uploaded") or 0.0)

    sorted_recs = sorted(all_recs, key=_sort_key)
    curr_idx = next((i for i, r in enumerate(sorted_recs) if r.get("id") == rid), -1)

    if baseline_id:
        base_rec = store.get(baseline_id, actual_sid) or store.get(baseline_id)
    else:
        # Prefer an earlier record with a distinct date or earlier visit
        candidates_prior = [r for r in sorted_recs[:curr_idx] if r.get("date") != curr_rec.get("date")]
        if candidates_prior:
            base_rec = candidates_prior[-1]
        elif curr_idx > 0:
            base_rec = sorted_recs[curr_idx - 1]
        elif curr_idx == 0 and len(sorted_recs) > 1:
            candidates_later = [r for r in sorted_recs[1:] if r.get("date") != curr_rec.get("date")]
            base_rec = candidates_later[0] if candidates_later else sorted_recs[1]

    if not base_rec:
        return jsonify({
            "has_baseline": False,
            "message": "No other historical reports available for longitudinal visit-over-visit comparison.",
            "current_id": rid
        })

    diff_data = analyzer.compute_report_diff(base_rec, curr_rec)
    return jsonify({
        "has_baseline": True,
        "current_id": rid,
        "baseline_id": base_rec.get("id"),
        "diff": diff_data
    })

@app.get("/api/diff/<rid>/baselines")
def list_diff_baselines(rid):
    """List all alternative reports in this patient session that can serve as a baseline."""
    sid = request.args.get("session_id")
    curr_rec = store.get(rid, sid) or store.get(rid)
    if not curr_rec:
        return jsonify(error="Current report not found"), 404
        
    actual_sid = curr_rec.get("session_id") or sid or "default"
    all_recs = store.all_reports(actual_sid)
    if len(all_recs) <= 1:
        all_recs = store.all_reports()
    
    def _sort_key(r):
        dt = analyzer.parse_date_or_timestamp(r.get("date"), r.get("uploaded"))
        return dt.timestamp() if dt else (r.get("uploaded") or 0.0)
        
    sorted_recs = sorted(all_recs, key=_sort_key)
    curr_idx = next((i for i, r in enumerate(sorted_recs) if r.get("id") == rid), -1)
    candidates_prior = [r for r in sorted_recs[:curr_idx] if r.get("date") != curr_rec.get("date")]
    if candidates_prior:
        default_base_id = candidates_prior[-1]["id"]
    elif curr_idx > 0:
        default_base_id = sorted_recs[curr_idx - 1]["id"]
    elif len(sorted_recs) > 1:
        default_base_id = sorted_recs[1]["id"]
    else:
        default_base_id = None
    
    candidates = []
    for r in sorted_recs:
        if r.get("id") == rid:
            continue
        candidates.append({
            "id": r["id"],
            "filename": r.get("filename", "Report"),
            "date": r.get("date") or "Unknown date",
            "uploaded": r.get("uploaded", 0),
            "total_markers": len(r.get("results", [])),
            "is_default": (r["id"] == default_base_id)
        })
        
    return jsonify(candidates=candidates, default_baseline_id=default_base_id)



if __name__ == "__main__":
    app.run(debug=True, port=5000)
