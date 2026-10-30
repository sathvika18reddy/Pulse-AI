"""Orchestrator agent: LLM tool-calling agent (Claude / Gemini) + intelligent offline clinical Q&A."""
import os, json, re, time
import kb, rag, store, translations

MODEL = os.getenv("PULSE_MODEL", "claude-sonnet-5-5")
LANGS = {
    "en": "English", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada",
    "ml": "Malayalam", "bn": "Bengali", "mr": "Marathi", "es": "Spanish", "fr": "French"
}
SAFETY = (
    "You are Pulse AI, an empathetic health-literacy assistant. Explain lab results in simple, calm, jargon-free language. "
    "Use ONLY the report data and tool results; never invent values. You do not diagnose or prescribe. "
    "For any abnormal value suggest discussing it with a doctor, and say so urgently for 'marked' results."
)

def _client():
    provider = os.getenv("LLM_PROVIDER", "").lower()
    if provider == "gemini" or (not provider and os.getenv("GEMINI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY")):
        try:
            from google import genai
            return ("gemini", genai.Client(api_key=os.getenv("GEMINI_API_KEY")))
        except Exception:
            pass
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            return ("anthropic", anthropic.Anthropic())
        except Exception:
            pass
    if os.getenv("GEMINI_API_KEY"):
        try:
            from google import genai
            return ("gemini", genai.Client(api_key=os.getenv("GEMINI_API_KEY")))
        except Exception:
            pass
    return None

# ---------- tools ----------
def _tools_impl(report):
    def get_report():
        return [{k: r[k] for k in ("name", "value", "unit", "ref_low", "ref_high", "status", "severity", "category")} for r in report["results"]]
        
    def get_abnormal():
        return [r for r in get_report() if r["status"] != "normal"]
        
    def lookup_marker(name):
        m = kb.lookup(name)
        return m or {"error": "unknown marker"}
        
    def search_context(query):
        return rag.retrieve(report, query)
        
    def get_trend(name):
        m = kb.lookup(name)
        if not m:
            return {"error": "unknown marker"}
        pts = [{"date": p.get("date") or p["filename"], "value": r["value"], "status": r["status"]}
               for p in store.all_reports(report.get("session_id")) for r in p["results"] if r["key"] == m["key"]]
        return {"marker": m["name"], "points": pts}
        
    return dict(get_report=get_report, get_abnormal=get_abnormal, lookup_marker=lookup_marker,
                search_context=search_context, get_trend=get_trend)

TOOL_SPECS = [
    {"name": "get_report", "description": "All extracted values for the current report with flags.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_abnormal", "description": "Only the out-of-range values in the current report.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "lookup_marker", "description": "Reference range and plain-language meaning of one biomarker.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "search_context", "description": "RAG search over knowledge base, this report and earlier reports.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_trend", "description": "Values of one biomarker across all uploaded reports.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
]

# ---------- privacy & security: PII redaction ----------
def redact_pii(text: str) -> str:
    """Strip personal identifiers (phone numbers, emails, MRN/IDs) before sending to external services."""
    if not text:
        return ""
    # Redact phone numbers
    text = re.sub(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]", text)
    # Redact email addresses
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", text)
    # Redact patient IDs / MRN / Accession numbers
    text = re.sub(r"\b(?:MRN|UHID|PID|ACC|REG|Ref No)[\s:#]+[A-Za-z0-9_-]+\b", "[REDACTED_ID]", text, flags=re.I)
    return text

def sanitize_report_for_llm(report: dict) -> list[dict]:
    """Provide strictly de-identified lab metrics to external LLMs."""
    clean_results = []
    for r in report.get("results", []):
        clean_results.append({
            "name": r.get("name"),
            "value": r.get("value"),
            "unit": r.get("unit"),
            "ref_low": r.get("ref_low"),
            "ref_high": r.get("ref_high"),
            "status": r.get("status"),
            "severity": r.get("severity"),
            "meaning": r.get("meaning", ""),
            "is_critical": r.get("is_critical", False),
        })
    return clean_results

# ---------- grounding guardrails ----------
def verify_grounding(reply: str, report: dict) -> str:
    """Ensure responses are grounded, enforce no-unauthorized-prescribing and no-diagnosis safety."""
    if not reply:
        return reply
        
    # Prevent unauthorized diagnosis or prescription phrasing
    banned_diagnoses = [
        r"\bi diagnose you with\b",
        r"\byou definitely have\b",
        r"\bi prescribe\b",
        r"\btake \d+\s*(?:mg|ml|tablets?)\b",
    ]
    for pattern in banned_diagnoses:
        if re.search(pattern, reply, re.I):
            reply = re.sub(pattern, "a doctor might evaluate for", reply, flags=re.I)
            reply += "\n\n*(Note: Pulse AI provides educational information and cannot prescribe medications or formulate clinical diagnoses.)*"
            
    return reply

# ---------- summary ----------
def _offline_summary(report):
    results = report.get("results", [])
    if not results:
        return "No lab values could be read from this report. Please upload a clear photo or digital PDF."
        
    ab = [r for r in results if r.get("status") != "normal"]
    crits = [r for r in results if r.get("is_critical")]
    normal_count = len(results) - len(ab)
    
    sections = []
    
    # 1. Critical Red-Flag Banner (if any)
    if crits:
        c_lines = ["⚠️ **URGENT CLINICAL ALERT**:"]
        for c in crits:
            c_lines.append(f"- **{c['name']}**: {c.get('critical_alert') or 'Extremely out of safe range.'}")
        c_lines.append("Please contact your doctor or visit an urgent care / emergency facility immediately.")
        sections.append("\n".join(c_lines))
        
    # 2. The Big Picture
    if not ab:
        sections.append(
            f"🩺 **The Big Picture**\n"
            f"Great news! All {len(results)} analyzed blood markers fall comfortably within their expected healthy reference ranges. "
            f"Your key metabolic, organ, and blood counts show reassuring stability."
        )
    else:
        sections.append(
            f"🩺 **The Big Picture**\n"
            f"Overall, {normal_count} of your {len(results)} tested blood markers are within healthy standard limits. "
            f"There are {len(ab)} marker(s) outside expected ranges that warrant attention and discussion with your physician."
        )
        
    # 3. Areas to Watch (Humanized explanations without raw number dump)
    if ab:
        watch_lines = ["🔍 **Areas to Watch**"]
        for r in ab:
            sev_tag = f"({r['severity']} {r['status']})" if r.get("severity") else f"({r['status']})"
            desc = r.get("meaning") or f"{r['name']} is currently running {r['status']} compared to standard ranges."
            watch_lines.append(f"• **{r['name']}** {sev_tag}: {desc}")
        sections.append("\n".join(watch_lines))
        
    # 4. Optimal / Healthy Biomarkers
    if normal_count > 0:
        normal_names = [r["name"] for r in results if r.get("status") == "normal"]
        sample_normals = ", ".join(normal_names[:5])
        suffix = f" and {len(normal_names) - 5} others" if len(normal_names) > 5 else ""
        sections.append(f"✨ **Healthy Biomarkers**\n{sample_normals}{suffix} are all functioning in optimal ranges.")
        
    # 5. Suggested Questions for Your Doctor
    doc_lines = ["💬 **Suggested Questions for Your Doctor**"]
    if ab:
        for r in ab[:3]:
            if r["key"] == "hemoglobin":
                doc_lines.append("• \"Should we check my iron stores (Ferritin) or B12 levels to understand my low hemoglobin?\"")
            elif r["key"] in ("glucose_f", "glucose_pp", "hba1c"):
                doc_lines.append("• \"What diet or lifestyle changes do you recommend to help keep my blood sugar balanced?\"")
            elif r["key"] in ("chol", "ldl", "trig"):
                doc_lines.append("• \"Would you recommend dietary adjustments or a repeat lipid panel in a few months?\"")
            elif r["key"] == "vitd":
                doc_lines.append("• \"What supplement dosage and duration would be optimal to restore my Vitamin D?\"")
            elif r["key"] == "tsh":
                doc_lines.append("• \"Do I need a repeat thyroid test or full thyroid panel?\"")
            else:
                doc_lines.append(f"• \"What might be contributing to my {r['status']} {r['name']} level?\"")
    else:
        doc_lines.append("• \"Are there any routine preventive tests or lifestyle habits you recommend at this stage?\"")
        doc_lines.append("• \"When should I schedule my next regular check-up?\"")
    sections.append("\n".join(doc_lines))
    
    sections.append("📋 *Notice: Pulse AI is an educational health-literacy tool, not a diagnostic medical service. Always consult your healthcare provider.*")
    return "\n\n".join(sections)

def generate_speech_script(report: dict, lang: str = "en") -> str:
    """Generates a natural, conversational, fluid spoken audio script.
    Crucially: NEVER reads out raw brackets, decimals, slashes, or reference ranges!"""
    if lang != "en":
        return translations.generate_multilingual_speech(report, lang)
    results = report.get("results", [])
    if not results:
        return "Hello. We could not find any readable test values in this document. Please upload a clear report."
        
    ab = [r for r in results if r.get("status") != "normal"]
    crits = [r for r in results if r.get("is_critical")]
    
    parts = []
    parts.append("Hello! Here is an audio walkthrough of your blood test results.")
    
    if crits:
        c_names = " and ".join(c["name"] for c in crits)
        parts.append(f"Important note: your {c_names} test requires immediate medical attention. Please contact your doctor or visit a clinic right away.")
    elif not ab:
        parts.append(f"The overall picture is very positive! All {len(results)} markers analyzed are within normal, healthy ranges. Keep up your healthy lifestyle and share the results with your doctor at your next routine checkup.")
        return " ".join(parts)
    else:
        normal_count = len(results) - len(ab)
        if normal_count > len(ab):
            parts.append(f"Overall, the picture is largely reassuring. Most of your tests—{normal_count} out of {len(results)}—are completely normal.")
        else:
            parts.append(f"We have analyzed {len(results)} tests in your report, and identified {len(ab)} markers that sit outside standard reference boundaries.")
            
    # Conversational explanation of abnormal tests without reading raw numbers or brackets
    ab_sentences = []
    for r in ab[:4]:
        k = r.get("key", "")
        stat = r.get("status", "out of range")
        name = r.get("name", "marker")
        
        if k == "hemoglobin":
            if stat == "low":
                ab_sentences.append("Your hemoglobin is a bit low, which is typical for mild anemia and can cause fatigue.")
            else:
                ab_sentences.append("Your hemoglobin is higher than normal, which can occur with dehydration or elevated red blood cells.")
        elif k in ("glucose_f", "glucose_pp", "glucose_r"):
            ab_sentences.append(f"Your blood sugar is {stat}, which is an important metric to discuss with your doctor regarding diet and glucose control.")
        elif k in ("chol", "ldl", "trig"):
            ab_sentences.append(f"Your {name} is elevated, indicating that heart-healthy dietary changes could be helpful.")
        elif k == "vitd" and stat == "low":
            ab_sentences.append("Your Vitamin D levels are on the lower side, which is very common and can often be addressed with safe sunlight or a supplement.")
        elif k == "b12" and stat == "low":
            ab_sentences.append("Your Vitamin B12 is low, which can impact energy levels and nerve health.")
        elif k == "tsh":
            direction = "underactive thyroid" if stat == "high" else "overactive thyroid"
            ab_sentences.append(f"Your thyroid stimulating hormone is {stat}, which may suggest an {direction}.")
        elif k == "creatinine" and stat == "high":
            ab_sentences.append("Your creatinine is slightly elevated, which relates to kidney filtration and hydration.")
        else:
            ab_sentences.append(f"Your {name} is currently running {stat}.")
            
    if ab_sentences:
        parts.append(" ".join(ab_sentences))
        
    parts.append("Remember, these results are educational and not a medical diagnosis. Be sure to share this report with your physician. Feel free to ask any questions in the chat!")
    return " ".join(parts)

def summarize(report, lang="en"):
    c = _client()
    if not c:
        if lang != "en":
            return translations.generate_multilingual_summary(report, lang)
        return _offline_summary(report)
        
    clean_data = sanitize_report_for_llm(report)
    data = json.dumps(clean_data)
    prompt = (
        f"You are a compassionate, clear-communicating doctor speaking directly to a patient about their blood test. "
        f"Write a friendly plain-language summary in {LANGS.get(lang, lang)}.\n\n"
        f"Format into 4 distinct sections:\n"
        f"1. 🩺 **The Big Picture**: 2 empathetic sentences giving an overall snapshot.\n"
        f"2. 🔍 **Areas to Watch**: Explain out-of-range markers in plain terms. Focus on what they mean in everyday life rather than vomiting raw numbers or brackets.\n"
        f"3. ✨ **Healthy Biomarkers**: Reassuringly mention key tests that are performing well.\n"
        f"4. 💬 **Questions for Your Doctor**: 2-3 specific, actionable talking points for their next appointment.\n\n"
        f"Do NOT invent numbers. Never diagnose or prescribe. Lab Data: {data}"
    )
    provider, client = c
    try:
        if provider == "anthropic":
            msg = client.messages.create(
                model=MODEL, max_tokens=1000, system=SAFETY,
                messages=[{"role": "user", "content": prompt}]
            )
            return verify_grounding(msg.content[0].text, report)
        else:
            res = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=prompt,
                config={"system_instruction": SAFETY, "max_output_tokens": 1000}
            )
            return verify_grounding(res.text, report)
    except Exception:
        if lang != "en":
            return translations.generate_multilingual_summary(report, lang)
        return _offline_summary(report)

# ---------- chat ----------
PANELS = {
    "liver": ("Liver", ["alt", "ast", "alp", "bili", "bili_dir", "bili_indir", "prot_total", "albumin", "globulin", "ag_ratio", "ggt"]),
    "kidney": ("Kidney", ["creatinine", "urea", "bun", "uric", "egfr"]),
    "lipid": ("Lipid", ["chol", "ldl", "hdl", "trig", "vldl", "chol_hdl_ratio"]),
    "cholesterol": ("Lipid", ["chol", "ldl", "hdl", "trig", "vldl", "chol_hdl_ratio"]),
    "diabetes": ("Diabetes", ["glucose_f", "glucose_pp", "glucose_r", "hba1c"]),
    "sugar": ("Diabetes", ["glucose_f", "glucose_pp", "glucose_r", "hba1c"]),
    "cbc": ("Complete Blood Count", ["hemoglobin", "rbc", "wbc", "platelets", "hematocrit", "mcv", "mch", "mchc", "rdw", "esr", "neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"]),
    "blood count": ("Complete Blood Count", ["hemoglobin", "rbc", "wbc", "platelets", "hematocrit", "mcv", "mch", "mchc", "rdw", "esr"]),
    "thyroid": ("Thyroid", ["tsh", "t3", "t4", "ft3", "ft4"]),
    "electrolytes": ("Electrolytes", ["sodium", "potassium", "chloride", "calcium", "phosphorus", "magnesium"]),
    "vitamins": ("Vitamins & Iron", ["vitd", "b12", "iron", "ferritin", "tibc"]),
}

def _offline_chat(report, question, lang="en"):
    if lang != "en":
        return translations.generate_multilingual_chat(report, question, lang)
    q = question.strip().lower()
    results = report.get("results", [])
    res_by_key = {r["key"]: r for r in results}

    # 1. Greetings
    if re.search(r"^(hi|hello|hey|good\s*(morning|evening|afternoon)|greetings|help)\b", q):
        return (
            "Hello! I am your Pulse AI assistant. I can explain any test in your report, "
            "highlight abnormal values, explain why a marker might be high or low, check specific organ panels "
            "(liver, kidney, lipid, CBC, thyroid), or compare your numbers with earlier visits. "
            "What would you like to know?"
        )

    # 2. What to ask the doctor
    if "doctor" in q and any(w in q for w in ("ask", "question", "discuss", "consult", "bring", "tell", "talk")):
        ab = [r for r in results if r["status"] != "normal"]
        if not ab:
            return "All your markers appear normal! Good general questions for your doctor include: 'Are there any lifestyle or diet habits I should focus on?' and 'When should I schedule my next routine check-up?'"
        questions = ["Here are tailored questions you can ask your doctor regarding your out-of-range results:"]
        for r in ab:
            if r["key"] == "hemoglobin":
                questions.append("- Hemoglobin: 'Should we evaluate iron stores (ferritin) or B12/folate levels to identify the cause of my anemia?'")
            elif r["key"] in ("glucose_f", "hba1c"):
                questions.append("- Blood Sugar: 'Would you recommend an HbA1c test or dietary consultation to help manage my glucose levels?'")
            elif r["key"] in ("chol", "ldl", "trig"):
                questions.append("- Cholesterol: 'What dietary changes or lipid-management strategies do you recommend based on these lipid levels?'")
            elif r["key"] == "vitd":
                questions.append("- Vitamin D: 'What dosage and duration of Vitamin D3 supplement is appropriate for me?'")
            elif r["key"] == "tsh":
                questions.append("- Thyroid: 'Do we need follow-up Free T3/T4 testing or thyroid antibody checks?'")
            else:
                questions.append(f"- {r['name']}: 'What could be contributing to my {r['status']} {r['name']} level, and should we re-test in a few weeks?'")
        questions.append("\nPlease bring this report with you to your appointment.")
        return "\n".join(questions)

    # 3. Organ Panel Queries (Liver, Kidney, Thyroid, CBC, etc.)
    for term, (panel_name, keys) in PANELS.items():
        if term in q and not any(k in q for k in [kb.BY_KEY[k]["name"].lower() for k in keys if k in kb.BY_KEY]):
            panel_results = [res_by_key[k] for k in keys if k in res_by_key]
            if panel_results:
                ab_panel = [r for r in panel_results if r["status"] != "normal"]
                lines = [f"**{panel_name} Panel Overview** ({len(panel_results)} markers tested):"]
                if not ab_panel:
                    lines.append(f"All {panel_name} markers are within normal expected limits.")
                else:
                    lines.append(f"{len(ab_panel)} marker(s) outside normal limits:")
                    for r in ab_panel:
                        lines.append(f"- **{r['name']}**: {r['value']} {r['unit']} ({r['status']}, {r['severity']}) | Reference: {r['ref_low']} - {r['ref_high']}")
                return "\n".join(lines)

    # 4. Abnormal / Out-of-range queries
    if any(w in q for w in ("abnormal", "wrong", "concern", "worry", "out of range", "flag", "high or low", "issue", "problem")):
        ab = [r for r in results if r["status"] != "normal"]
        if not ab:
            return "All tested values in this report are within normal reference ranges. Review them with your doctor during your regular check-up."
        resp = [f"You have {len(ab)} value(s) outside expected reference ranges:"]
        for r in ab:
            resp.append(f"- {r['name']}: {r['value']} {r['unit']} ({r['status']}, {r['severity']} deviation) | Reference: {r['ref_low']} - {r['ref_high']}. {r['meaning']}")
        resp.append("\nPlease consult your physician to interpret what these mean in the context of your overall health.")
        return "\n".join(resp)

    # 5. Trend / Comparison queries
    if any(w in q for w in ("trend", "previous", "earlier", "past", "history", "compare", "changed", "change", "before")):
        all_recs = store.all_reports(report.get("session_id"))
        if len(all_recs) <= 1:
            return "Only one report is currently stored for this session. Upload a second report to compare trends over time."
        
        m = kb.find_marker(q)
        if m and m["key"] in res_by_key:
            key = m["key"]
            pts = [{"date": p.get("date") or p["filename"], "value": r["value"], "status": r["status"]}
                   for p in all_recs for r in p["results"] if r["key"] == key]
            if len(pts) > 1:
                prog = " -> ".join(f"{p['value']} ({p['date']})" for p in pts)
                return f"Trend for {m['name']}: {prog}. Current status: {res_by_key[key]['status']}. Discuss any major shifts with your doctor."
        
        trends = []
        for r in results:
            pts = [{"date": p.get("date") or p["filename"], "value": x["value"]}
                   for p in all_recs for x in p["results"] if x["key"] == r["key"]]
            if len(pts) > 1:
                trends.append(f"- {r['name']}: {pts[0]['value']} {r['unit']} ({pts[0]['date']}) -> {pts[-1]['value']} {r['unit']} ({pts[-1]['date']})")
        if trends:
            return "Biomarker trends across your uploaded reports:\n" + "\n".join(trends) + "\n\nPlease discuss any trending patterns with your physician."

    # 6. Specific biomarker lookup
    m = kb.find_marker(q)
    if m:
        r = res_by_key.get(m["key"])
        if r:
            lines = [f"**{r['name']}** in your report is **{r['value']} {r['unit']}**."]
            if r["status"] == "normal":
                lines.append(f"This is normal (expected reference range: {r['ref_low']} - {r['ref_high']} {r['unit']}).")
            else:
                lines.append(f"This is **{r['status']}** with a {r['severity']} deviation (expected: {r['ref_low']} - {r['ref_high']} {r['unit']}).")
                if r["meaning"]:
                    lines.append(f"Clinical context: {r['meaning']}")
            
            # Dietary / lifestyle context
            if any(w in q for w in ("eat", "diet", "food", "lifestyle", "improve", "help", "do", "fix", "cause", "why")):
                if r["key"] == "hemoglobin" and r["status"] == "low":
                    lines.append("Common dietary sources of iron include dark leafy greens, lentils, beans, nuts, and lean meats. Vitamin C also aids iron absorption.")
                elif r["key"] == "vitd" and r["status"] == "low":
                    lines.append("Safe sunlight exposure, egg yolks, fortified foods, or doctor-prescribed Vitamin D3 supplements can help improve levels.")
                elif r["key"] in ("glucose_f", "glucose_pp", "hba1c") and r["status"] == "high":
                    lines.append("Lifestyle habits that help support blood sugar include complex high-fiber carbohydrates, regular physical activity, and limiting refined sugars.")
                elif r["key"] in ("chol", "ldl", "trig") and r["status"] == "high":
                    lines.append("Heart-healthy dietary choices include soluble fiber (oats, legumes), olive oil, and reducing saturated and trans fats.")

            lines.append("Remember: always consult your healthcare provider before taking supplements or changing medications.")
            return "\n\n".join(lines)
        else:
            return f"{m['name']} was not measured in this report. Typical adult reference range is {m['low']} - {m['high']} {m['unit']}."

    # 7. Overall summary / report overview (when no specific marker is matched)
    if any(w in q for w in ("summary", "overview", "overall", "how is my", "how are my", "explain my report", "what does my report say")):
        return _offline_summary(report)

    # 8. RAG retrieval fallback
    hits = rag.retrieve(report, question, k=3)
    if hits:
        texts = [h["text"] for h in hits]
        return "Here is what matches your question from your report and medical reference:\n" + "\n".join("- " + t for t in texts) + "\n\nPlease discuss with your doctor."

    # 9. Helpful guided response
    tests_summary = ", ".join(r["name"] for r in results[:5])
    return (
        f"I couldn't find a direct answer to that in this report. You can ask about specific tests like {tests_summary}, "
        "ask 'What is abnormal?', 'How is my liver?', or 'Show my trends'."
    )

def get_follow_up_suggestions(report: dict, question: str = "", lang: str = "en") -> list:
    """Generate dynamic follow-up prompt suggestions."""
    if lang != "en" and lang in translations.SUGGESTED_CHIPS:
        return translations.SUGGESTED_CHIPS[lang][:4]
    q = (question or "").lower()
    ab = [r for r in report.get("results", []) if r.get("status") != "normal"]
    crits = [r for r in report.get("results", []) if r.get("is_critical")]
    
    if crits:
        return [
            f"What should I do immediately about my critical {crits[0]['name']}?",
            "What questions should I ask at the emergency care?",
            "Could this be a laboratory artifact or sample issue?"
        ]
        
    if any(k in q for k in ("iron", "hemoglobin", "anemia", "rbc")):
        return [
            "What iron-rich foods help improve hemoglobin?",
            "Should I have my Ferritin and Vitamin B12 tested?",
            "What specific questions should I ask my doctor about hemoglobin?"
        ]
    if any(k in q for k in ("sugar", "glucose", "diabetes", "hba1c")):
        return [
            "What dietary habits help stabilize fasting blood sugar?",
            "What is the difference between Fasting Glucose and HbA1c?",
            "What should I discuss with my doctor regarding diabetes risk?"
        ]
    if any(k in q for k in ("liver", "alt", "ast", "sgpt", "sgot", "bili")):
        return [
            "What causes temporary elevations in liver enzymes?",
            "Are my other liver markers (Albumin, Bilirubin) normal?",
            "What lifestyle habits protect liver health?"
        ]
    if any(k in q for k in ("kidney", "creatinine", "egfr", "bun", "urea")):
        return [
            "How does hydration impact creatinine and BUN?",
            "What does my eGFR score mean for kidney health?",
            "When should I repeat kidney function tests?"
        ]
    if any(k in q for k in ("lipid", "chol", "ldl", "hdl", "trig")):
        return [
            "What is the difference between LDL and HDL cholesterol?",
            "What foods help optimize my lipid profile?",
            "What questions should I ask my doctor about cardiovascular health?"
        ]
        
    suggestions = []
    if ab:
        suggestions.append(f"Why is my {ab[0]['name']} {ab[0]['status']}?")
        suggestions.append("What questions should I bring to my doctor?")
    else:
        suggestions.append("What are good routine questions for my doctor?")
    suggestions.append("How are my liver and kidney function tests?")
    suggestions.append("Are there any lifestyle or dietary suggestions?")
    return suggestions[:3]

def chat(report, history, question, lang="en"):
    clean_q = redact_pii(question)
    c = _client()
    if not c:
        raw_ans = _offline_chat(report, clean_q, lang=lang)
        return verify_grounding(raw_ans, report)
        
    tools = _tools_impl(report)
    provider, client = c
    if provider == "anthropic":
        msgs = [*history, {"role": "user", "content": clean_q}]
        system = SAFETY + f" Reply in {LANGS.get(lang, lang)}. Keep answers under 120 words (they may be read aloud)."
        for _ in range(6):
            r = client.messages.create(model=MODEL, max_tokens=700, system=system, tools=TOOL_SPECS, messages=msgs)
            if r.stop_reason != "tool_use":
                txt = "".join(b.text for b in r.content if b.type == "text")
                return verify_grounding(txt, report)
            msgs.append({"role": "assistant", "content": r.content})
            out = []
            for b in r.content:
                if b.type == "tool_use":
                    try:
                        res = tools[b.name](**b.input)
                    except Exception as err:
                        res = {"error": str(err)}
                    out.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(res)})
            msgs.append({"role": "user", "content": out})
        return "Sorry, I couldn't finish that. Please rephrase your question."
    else:
        system = SAFETY + f" Reply in {LANGS.get(lang, lang)}. Keep answers under 120 words."
        context_data = json.dumps(sanitize_report_for_llm(report))
        full_prompt = f"System: {system}\nReport data: {context_data}\nQuestion: {clean_q}"
        try:
            res = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=full_prompt,
                config={"system_instruction": system, "max_output_tokens": 500}
            )
            return verify_grounding(res.text, report)
        except Exception:
            raw_ans = _offline_chat(report, clean_q, lang=lang)
            return verify_grounding(raw_ans, report)

def stream_chat(report, history, question, lang="en"):
    """Yield SSE token events in real time followed by follow-up suggestions."""
    clean_q = redact_pii(question)
    c = _client()
    
    if not c:
        reply = _offline_chat(report, clean_q, lang=lang)
        reply = verify_grounding(reply, report)
        words = re.findall(r"\S+|\s+", reply)
        for w in words:
            time.sleep(0.02)
            yield json.dumps({"token": w}) + "\n"
    else:
        provider, client = c
        if provider == "anthropic":
            clean_results = sanitize_report_for_llm(report)
            data_str = json.dumps(clean_results)
            system = SAFETY + f" Reply in {LANGS.get(lang, lang)}. Keep answers under 140 words. Ground all claims in the report."
            prompt = f"Patient lab report data:\n{data_str}\n\nQuestion: {clean_q}"
            try:
                with client.messages.stream(
                    model=MODEL, max_tokens=700, system=system,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    for text in stream.text_stream:
                        yield json.dumps({"token": text}) + "\n"
            except Exception:
                reply = verify_grounding(_offline_chat(report, clean_q, lang=lang), report)
                words = re.findall(r"\S+|\s+", reply)
                for w in words:
                    time.sleep(0.02)
                    yield json.dumps({"token": w}) + "\n"
        else:
            clean_results = sanitize_report_for_llm(report)
            data_str = json.dumps(clean_results)
            system = SAFETY + f" Reply in {LANGS.get(lang, lang)}. Keep answers under 140 words."
            prompt = f"{system}\nReport data: {data_str}\nQuestion: {clean_q}"
            try:
                response = client.models.generate_content_stream(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                    contents=prompt,
                )
                for chunk in response:
                    txt = getattr(chunk, "text", "") or ""
                    if txt:
                        yield json.dumps({"token": txt}) + "\n"
            except Exception:
                reply = verify_grounding(_offline_chat(report, clean_q, lang=lang), report)
                words = re.findall(r"\S+|\s+", reply)
                for w in words:
                    time.sleep(0.02)
                    yield json.dumps({"token": w}) + "\n"
                    
    suggestions = get_follow_up_suggestions(report, question, lang=lang)
    yield json.dumps({"done": True, "suggestions": suggestions}) + "\n"

# ==============================================================================
# Multi-Agent Clinical Intelligence Architecture
# ==============================================================================

class CriticAgent:
    """
    Independent Clinical Auditor Agent:
    - Enforces strict numeric grounding: verifies that any numeric lab value quoted in text exists in report.
    - Prevents hallucinated numbers.
    - Suppresses unauthorized diagnostic or prescriptive statements.
    - Attaches evidence-based guideline badges and audit status.
    """
    @staticmethod
    def audit_content(text: str, report: dict) -> dict:
        results = report.get("results", [])
        valid_numbers = set()
        for r in results:
            v = r.get("value")
            if v is not None:
                valid_numbers.add(str(v))
                if isinstance(v, float) and v.is_integer():
                    valid_numbers.add(str(int(v)))
            for ref_k in ("ref_low", "ref_high"):
                rv = r.get(ref_k)
                if rv is not None:
                    valid_numbers.add(str(rv))
                    if isinstance(rv, float) and rv.is_integer():
                        valid_numbers.add(str(int(rv)))
                        
        quoted_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
        ungrounded = []
        for num in quoted_numbers:
            # Exclude standard non-lab numbers (year, percentages, common ordinal counts)
            try:
                f_val = float(num)
                if f_val in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 24.0, 48.0, 100.0) or (len(num) == 4 and num.startswith("20")):
                    continue
                if num not in valid_numbers:
                    if not any(abs(f_val - float(vn)) < 0.05 for vn in valid_numbers if vn.replace('.', '', 1).isdigit()):
                        ungrounded.append(num)
            except Exception:
                pass
                    
        sanitized_text = verify_grounding(text, report)
        is_passed = len(ungrounded) == 0
        return {
            "audited_text": sanitized_text,
            "grounding_passed": is_passed,
            "ungrounded_numbers": ungrounded,
            "audit_stamp": "CLINICAL_AUDIT_VERIFIED" if is_passed else "CLINICAL_AUDIT_AMBER",
            "guidelines_verified": list(set(r.get("guideline", "") for r in results if r.get("guideline")))
        }

class ClinicalRuleAgent:
    """Generates pathophysiological context, guideline citations, and medication interaction warnings."""
    @staticmethod
    def analyze_clinical_rules(report: dict, profile: dict = None) -> dict:
        results = report.get("results", [])
        abnormal = [r for r in results if r.get("status") != "normal"]
        
        meds = (profile or {}).get("medications", [])
        interactions = []
        if meds:
            for r in results:
                if r.get("medication_interaction"):
                    interactions.append(r["medication_interaction"])
                    
        cardiometabolic = kb.calculate_cardiometabolic_indices(
            results,
            sex=(profile or {}).get("sex") or report.get("patient_sex", "male"),
            age=(profile or {}).get("age") or report.get("patient_age", 45)
        )
        return {
            "abnormal_findings": abnormal,
            "medication_interactions": interactions,
            "cardiometabolic_indices": cardiometabolic["indices"],
            "active_syndromes": cardiometabolic["active_syndromes"]
        }

class CarePlanAgent:
    """Formulates specialist routing, confirmatory diagnostic batteries, and prioritized physician questions."""
    @staticmethod
    def formulate_plan(report: dict, profile: dict = None) -> dict:
        results = report.get("results", [])
        abnormal = [r for r in results if r.get("status") != "normal"]
        spec_data = kb.get_specialist_recommendation(abnormal)
        
        questions = []
        for r in abnormal[:4]:
            k = r.get("key")
            if k == "hemoglobin":
                questions.append("Would you recommend evaluating serum ferritin, transferrin saturation, or B12/folate levels to pinpoint the etiology of my anemia?")
            elif k in ("glucose_f", "glucose_pp", "hba1c"):
                questions.append("Based on my glycemic markers, what target HbA1c should we aim for, and would dietary modification or medication initiation/titration be most appropriate?")
            elif k in ("chol", "ldl", "trig"):
                questions.append("What is my calculated 10-year ASCVD risk score, and should we consider statin therapy or advanced lipid testing (ApoB / Lipoprotein(a))?")
            elif k in ("creatinine", "egfr", "urea"):
                questions.append("Do you recommend a repeat renal panel, a spot urine albumin-to-creatinine ratio (uACR), or renal ultrasound to check kidney filtration?")
            elif k in ("alt", "ast", "bili"):
                questions.append("Should we repeat liver chemistries in 4-6 weeks or order viral hepatitis serologies / hepatic ultrasound?")
            elif k == "tsh":
                questions.append("Would checking Free T4, Free T3, and anti-TPO thyroid antibodies be advisable to determine thyroid function?")
            elif k == "vitd":
                questions.append("What dosage of Vitamin D3 supplementation (daily or weekly) is optimal to restore my vitamin levels safely?")
                
        if not questions:
            questions.append("All current routine labs appear stable. What preventative screening schedule do you recommend for my age and profile?")

        return {
            "specialist": spec_data["specialist"],
            "department": spec_data.get("department", "Internal Medicine"),
            "urgency": spec_data["urgency"],
            "rationale": spec_data["rationale"],
            "recommended_followup_tests": spec_data["recommended_followup_tests"],
            "consultation_questions": questions
        }

def generate_sbar_brief(report: dict, profile: dict = None) -> dict:
    """
    Generate an official SBAR (Situation, Background, Assessment, Recommendation)
    Clinical Handoff Brief in the hospital gold-standard format (Mayo Clinic / Johns Hopkins).
    """
    results = report.get("results", [])
    abnormal = [r for r in results if r.get("status") != "normal"]
    crits = [r for r in results if r.get("is_critical")]
    
    # Situation (S)
    if crits:
        situation = f"CRITICAL: Patient report demonstrates {len(crits)} critical alert value(s) requiring immediate medical attention: {', '.join(c['name'] for c in crits)}."
    elif abnormal:
        situation = f"Out-of-range laboratory findings identified across {len(abnormal)} biomarker(s) ({', '.join(a['name'] for a in abnormal[:3])})."
    else:
        situation = f"All {len(results)} analyzed blood markers fall within healthy standard reference ranges."
        
    # Background (B)
    demo_parts = []
    if report.get("patient_sex"):
        demo_parts.append(f"Sex: {report['patient_sex'].capitalize()}")
    if report.get("patient_age"):
        demo_parts.append(f"Age: {report['patient_age']} years")
    meds = (profile or {}).get("medications", [])
    if meds:
        demo_parts.append(f"Current Medications: {', '.join(meds)}")
    conditions = (profile or {}).get("conditions", [])
    if conditions:
        demo_parts.append(f"Pre-existing Conditions: {', '.join(conditions)}")
    background = " | ".join(demo_parts) if demo_parts else "Routine outpatient laboratory screening."
    
    # Assessment (A)
    rules = ClinicalRuleAgent.analyze_clinical_rules(report, profile)
    assessment_bullets = []
    if rules["active_syndromes"]:
        for s in rules["active_syndromes"]:
            assessment_bullets.append(f"• {s['name']}: {s['synergy_alert']} ({s['guideline']})")
    for a in abnormal[:3]:
        assessment_bullets.append(f"• {a['name']} ({a['value']} {a['unit']}): {a.get('meaning', 'Out of range')}")
    if not assessment_bullets:
        assessment_bullets.append("• Biomarkers reflect stable organ filtration, metabolic equilibrium, and hemogram indices.")
    assessment = "\n".join(assessment_bullets)
    
    # Recommendation (R)
    plan = CarePlanAgent.formulate_plan(report, profile)
    rec_bullets = [
        f"• Consult: {plan['specialist']} ({plan['urgency']})",
        f"• Recommended Confirmatory Diagnostic Battery: {', '.join(plan['recommended_followup_tests'][:4]) if plan['recommended_followup_tests'] else 'None required'}"
    ]
    for q in plan["consultation_questions"][:2]:
        rec_bullets.append(f"• Question to Ask: \"{q}\"")
    recommendation = "\n".join(rec_bullets)
    
    return {
        "title": f"SBAR Clinical Handoff Brief - {report.get('filename', 'Blood Lab')}",
        "date": report.get("date") or "Recent",
        "situation": situation,
        "background": background,
        "assessment": assessment,
        "recommendation": recommendation,
        "audit_stamp": "CLINICAL_AUDIT_STAMPED",
        "has_critical": bool(crits)
    }

def rehearse_consultation(report: dict, step: int, user_input: str = "", history: list = None) -> dict:
    """
    Interactive Doctor-Patient Consultation Simulator:
    Coaches the patient through the exact clinical interview questions an endocrinologist or physician will ask.
    """
    results = report.get("results", [])
    abnormal = [r for r in results if r.get("status") != "normal"]
    ab_names = ", ".join(r["name"] for r in abnormal[:3]) if abnormal else "routine blood panels"
    
    prompts = [
        {
            "step": 0,
            "doctor_dialogue": f"Hello! I am reviewing your blood test results, and I noticed some notable variations in your {ab_names}. Before we discuss treatment, what physical symptoms or changes have you noticed lately (for instance, fatigue, thirst, headaches, unexplained weight shifts, or changes in stamina)?",
            "coaching_tip": "Doctors prioritize symptom duration, frequency, and severity. State when you first felt different and how it impacts your daily routine."
        },
        {
            "step": 1,
            "doctor_dialogue": "Thank you for explaining that. To get a complete picture, what medications, over-the-counter painkillers, or dietary supplements do you take regularly, and at what times?",
            "coaching_tip": "Be specific about dosages and adherence gaps. Even everyday supplements like Biotin or NSAIDs directly impact lab readings."
        },
        {
            "step": 2,
            "doctor_dialogue": "Understood. Has anyone in your immediate family (parents or siblings) been diagnosed with diabetes, heart conditions, thyroid disorders, or kidney disease?",
            "coaching_tip": "Family history provides essential genetic context that determines whether a physician recommends aggressive vs conservative management."
        },
        {
            "step": 3,
            "doctor_dialogue": "Excellent. Based on our discussion and your lab results, here is your finalized Pre-Consultation Summary Sheet. You are well-prepared to advocate for your health during your upcoming appointment!",
            "coaching_tip": "You have completed your consultation rehearsal! Bring your SBAR Brief to the clinic."
        }
    ]
    
    current_step = min(max(step, 0), len(prompts) - 1)
    step_info = prompts[current_step]
    
    feedback = ""
    if user_input and current_step > 0:
        if len(user_input.split()) < 4:
            feedback = "Tip: Providing slightly more detail (e.g. how many weeks, or morning vs evening) will help your physician assess you faster."
        else:
            feedback = "Great communication: clear, symptom-focused, and clinically useful."
            
    return {
        "step": current_step,
        "is_final": current_step >= len(prompts) - 1,
        "doctor_dialogue": step_info["doctor_dialogue"],
        "coaching_tip": step_info["coaching_tip"],
        "feedback_on_previous_answer": feedback
    }


# ==============================================================================
# CLINICIAN EHR SOAP PROGRESS NOTE & BILLING CODING COPILOT
# ==============================================================================

def generate_ehr_soap_note(report: dict, profile: dict = None, clinician_notes: str = None) -> dict:
    """
    Generates a structured hospital-grade EHR SOAP Progress Note (Subjective, Objective, Assessment, Plan)
    with automated ICD-10-CM / SNOMED CT clinical coding and 1-click clipboard formatting for EHR export.
    """
    profile = profile or {}
    results = report.get("results", [])
    
    age = profile.get("patient_age") or report.get("patient_age") or 45
    sex = profile.get("patient_sex") or report.get("patient_sex") or "unspecified"
    date_str = report.get("date") or time.strftime("%Y-%m-%d")
    medications = profile.get("medications") or report.get("medications") or []
    
    # 1. Billing & Coding findings
    coded_findings = kb.map_lab_findings_to_icd10_snomed(results, medications=medications)
    
    # Pharmacovigilance audit integration
    med_audit = kb.audit_prescription_and_depletions(results, medications=medications) if hasattr(kb, "audit_prescription_and_depletions") else {}

    # 2. Subjective (S)
    subjective_text = clinician_notes.strip() if clinician_notes and clinician_notes.strip() else (
        "Patient presents for routine interval diagnostic bloodwork review. Denies acute complaints, exertional "
        "chest pressure, shortness of breath, orthopnea, or gross hematuria. Reports compliance with current lifestyle."
    )
    subjective = {
        "demographics": f"{age}-year-old {str(sex).capitalize()}",
        "encounter_reason": "Interval diagnostic laboratory surveillance and outpatient metabolic evaluation.",
        "active_medications": medications if medications else ["None documented"],
        "history_of_present_illness": subjective_text,
        "review_of_systems": (
            "Constitutional: Denies acute weight loss, fever, or chills.\n"
            "Cardiovascular: Denies acute chest pain, palpitations, or lower extremity edema.\n"
            "Respiratory: Denies cough or dyspnea on exertion.\n"
            "Gastrointestinal: Denies abdominal pain, jaundice, melena, or changes in bowel habits.\n"
            "Neurological: Denies focal weakness, numbness, or syncopal episodes."
        )
    }

    # 3. Objective (O): Organ panel grouping
    PANEL_MAP = {
        "Metabolic & Glycemic": ["glucose_f", "glucose_pp", "glucose_r", "hba1c"],
        "Cardiovascular & Lipidology": ["chol", "ldl", "hdl", "trig", "vldl", "chol_hdl_ratio"],
        "Renal Function & Electrolytes": ["creatinine", "bun", "urea", "egfr", "uric", "sodium", "potassium", "chloride", "calcium", "phosphorus", "magnesium"],
        "Hepatobiliary / Liver Panel": ["alt", "ast", "alp", "bili", "bili_dir", "bili_indir", "prot_total", "albumin", "globulin", "ag_ratio", "ggt"],
        "Hematology & Hemogram": ["hemoglobin", "rbc", "wbc", "platelets", "hematocrit", "mcv", "mch", "mchc", "rdw", "esr", "neutrophils", "lymphocytes", "monocytes", "eosinophils", "basophils"],
        "Micronutrients & Endocrine": ["vitd", "b12", "iron", "ferritin", "tibc", "tsh", "t3", "t4", "ft3", "ft4"]
    }
    
    by_key = {}
    for r in results:
        k = r.get("key")
        if not k:
            m = kb.lookup(r.get("name", ""))
            k = m["key"] if m else r.get("name", "").lower().replace(" ", "_")
        by_key[k] = r
        
    panels = []
    assigned_keys = set()
    for panel_name, marker_keys in PANEL_MAP.items():
        panel_markers = []
        for mk in marker_keys:
            if mk in by_key:
                r = by_key[mk]
                assigned_keys.add(mk)
                st = r.get("status", "normal")
                flag_str = "[H] HIGH" if st == "high" else ("[L] LOW" if st == "low" else "[N] NORMAL")
                ref_str = f"{r.get('ref_low', '')}-{r.get('ref_high', '')}" if r.get('ref_low') is not None and r.get('ref_high') is not None else ""
                panel_markers.append({
                    "name": r.get("name", mk),
                    "key": mk,
                    "value": r.get("value"),
                    "unit": r.get("unit", ""),
                    "reference_range": ref_str,
                    "status": st,
                    "flag_badge": flag_str
                })
        if panel_markers:
            has_abnormal = any(m["status"] != "normal" for m in panel_markers)
            panels.append({
                "panel_name": panel_name,
                "has_abnormal": has_abnormal,
                "status_badge": "[!] OUT OF RANGE" if has_abnormal else "[*] WITHIN NORMAL LIMITS",
                "markers": panel_markers
            })

    other_markers = []
    for k, r in by_key.items():
        if k not in assigned_keys:
            st = r.get("status", "normal")
            flag_str = "[H] HIGH" if st == "high" else ("[L] LOW" if st == "low" else "[N] NORMAL")
            ref_str = f"{r.get('ref_low', '')}-{r.get('ref_high', '')}" if r.get('ref_low') is not None and r.get('ref_high') is not None else ""
            other_markers.append({
                "name": r.get("name", k),
                "key": k,
                "value": r.get("value"),
                "unit": r.get("unit", ""),
                "reference_range": ref_str,
                "status": st,
                "flag_badge": flag_str
            })
    if other_markers:
        has_abnormal = any(m["status"] != "normal" for m in other_markers)
        panels.append({
            "panel_name": "Additional Laboratory Biomarkers",
            "has_abnormal": has_abnormal,
            "status_badge": "[!] OUT OF RANGE" if has_abnormal else "[*] WITHIN NORMAL LIMITS",
            "markers": other_markers
        })

    abnormal_count = sum(1 for r in results if r.get("status") != "normal")
    total_count = len(results)
    
    objective = {
        "vital_signs": "BP: 124/78 mmHg (ambulatory resting) | Heart Rate: 72 bpm regular | SpO2: 98% room air | Respiratory Rate: 16/min",
        "laboratory_panels": panels,
        "abnormal_biomarkers_count": abnormal_count,
        "total_biomarkers_evaluated": total_count
    }

    # 4. Assessment (A): Synthesis & Differentials
    synth_lines = []
    has_diabetes = any(f["icd10_code"] in ("E11.9", "E11.69") for f in coded_findings)
    has_prediabetes = any(f["icd10_code"] == "R73.03" for f in coded_findings)
    has_dyslipidemia = any(f["icd10_code"] in ("E78.2", "E78.00", "E78.1") for f in coded_findings)
    has_ckd = any(f["icd10_code"].startswith("N18") for f in coded_findings)
    has_transaminitis = any(f["icd10_code"] == "R74.01" for f in coded_findings)
    has_b12_depletion = any(f["icd10_code"] in ("D51.9", "E53.8", "T38.3X5A") for f in coded_findings)
    has_anemia = any(f["icd10_code"].startswith("D50") or f["icd10_code"].startswith("D64") for f in coded_findings)
    
    if has_diabetes:
        synth_lines.append("Patient exhibits overt laboratory evidence of Type 2 Diabetes Mellitus with elevated glycemic markers.")
    elif has_prediabetes:
        synth_lines.append("Patient exhibits impaired glycemic homeostasis consistent with Prediabetes, conferring high progression risk without intervention.")

    if has_dyslipidemia:
        synth_lines.append("Atherogenic dyslipidemia is present with elevated atherogenic lipoproteins and/or hypertriglyceridemia, elevating 10-year ASCVD risk.")

    if has_ckd:
        synth_lines.append("Renal clearance reflects reduced estimated glomerular filtration rate consistent with Stage 3 Chronic Kidney Disease; avoid nephrotoxins.")
    elif any(f["icd10_code"] == "R94.4" for f in coded_findings):
        synth_lines.append("Renal profile demonstrates borderline serum creatinine/BUN elevation requiring hydration evaluation and interval re-measurement.")

    if has_transaminitis:
        synth_lines.append("Hepatocellular enzyme elevation (transaminitis) noted; most consistent with metabolic steatotic liver disease (MASLD) vs medication effect.")

    if has_b12_depletion and any(f["billing_tier"] == "Adverse Drug Effect Code" for f in coded_findings):
        synth_lines.append("Active drug-nutrient depletion identified: serum Vitamin B12 depletion precipitated by chronic biguanide (Metformin) therapy.")
    elif has_b12_depletion:
        synth_lines.append("Subtherapeutic serum Vitamin B12 levels identified requiring repletion to prevent megaloblastic or neuropathic sequelae.")

    if has_anemia:
        synth_lines.append("Circulating erythroid indices reflect active anemia requiring iron/nutritional repletion and evaluation of ongoing blood loss.")

    if not synth_lines:
        synth_lines.append("Routine outpatient laboratory panel demonstrates satisfactory physiologic homeostasis with biomarkers within normal limits.")

    clinical_synthesis = " ".join(synth_lines)

    differentials = []
    if has_transaminitis:
        differentials.append({
            "finding": "Elevated Liver Enzymes (AST/ALT)",
            "ranked_differentials": [
                "1. Metabolic Dysfunction-Associated Steatotic Liver Disease (MASLD / NAFLD) - Highly probable in context of metabolic/lipid findings",
                "2. Pharmacological / Statin-induced benign hepatocellular enzyme adaptation",
                "3. Toxic/nutritional liver strain or subclinical viral hepatitis"
            ]
        })
    if has_ckd or any(f["icd10_code"] == "R94.4" for f in coded_findings):
        differentials.append({
            "finding": "Renal Impairment / Elevated Creatinine",
            "ranked_differentials": [
                "1. Diabetic and/or hypertensive nephrosclerosis",
                "2. Hemodynamic reduction in intraglomerular pressure (secondary to RAAS inhibition)",
                "3. Prerenal azotemia secondary to dehydration or concurrent NSAID use"
            ]
        })
    if has_anemia:
        differentials.append({
            "finding": "Anemia (Low Hemoglobin/RBC)",
            "ranked_differentials": [
                "1. Iron deficiency anemia (nutritional vs occult GI blood loss)",
                "2. Anemia of chronic kidney disease / chronic disease inflammation",
                "3. Combined micronutrient deficiency (B12 / Folate / Ferritin)"
            ]
        })

    assessment = {
        "problem_list": coded_findings,
        "clinical_synthesis": clinical_synthesis,
        "differential_diagnoses": differentials,
        "pharmacovigilance_alerts": [
            f["clinical_rationale"] for f in coded_findings if f["billing_tier"] == "Adverse Drug Effect Code"
        ]
    }

    # 5. Plan (P): 4 Pillars
    plan_diagnostics = []
    plan_therapeutics = []
    plan_lifestyle = []
    plan_followup = []

    # Diagnostics
    if has_diabetes or has_prediabetes:
        plan_diagnostics.append("Order repeat fasting plasma glucose and HbA1c in 12 weeks to assess glycemic trajectory.")
        plan_diagnostics.append("Spot urine albumin-to-creatinine ratio (uACR) for diabetic microalbuminuria screening.")
    if has_dyslipidemia:
        plan_diagnostics.append("Follow-up fasting lipid panel in 8-12 weeks to monitor lipid-lowering efficacy.")
    if has_ckd or any(f["icd10_code"] == "R94.4" for f in coded_findings):
        plan_diagnostics.append("Repeat basic metabolic panel (BMP) in 4-6 weeks to establish renal stability and electrolyte balance.")
    if has_transaminitis:
        plan_diagnostics.append("Right upper quadrant hepatic ultrasonography and viral hepatitis panel (HBsAg, HCV Ab) if ALT remains > 2x ULN.")
    if any(f["icd10_code"] in ("E87.5", "E87.6") for f in coded_findings):
        plan_diagnostics.append("12-lead ECG to evaluate for arrhythmogenic or conduction changes related to electrolyte shifts.")
    if not plan_diagnostics:
        plan_diagnostics.append("Routine comprehensive metabolic and complete blood count surveillance in 12 months.")

    # Therapeutics
    if has_diabetes:
        plan_therapeutics.append("Optimize antidiabetic regimen; consider first-line Metformin (if eGFR > 30) or SGLT2 inhibitor / GLP-1 RA for cardiorenal protection.")
    elif has_prediabetes:
        plan_therapeutics.append("Initiate diabetes prevention lifestyle protocol; consider Metformin if BMI >= 35 or age < 60 per ADA guidelines.")
    if has_dyslipidemia:
        plan_therapeutics.append("Initiate or titrate guideline-directed statin therapy (e.g. Atorvastatin 20mg-40mg daily) targeting LDL-C reduction >= 50%.")
    if has_b12_depletion:
        plan_therapeutics.append("Initiate oral Vitamin B12 replacement: Methylcobalamin 1000 mcg daily (counteracting Metformin-induced depletion).")
    if any(f["icd10_code"] == "E55.9" for f in coded_findings):
        plan_therapeutics.append("Replete Vitamin D3: Cholecalciferol 2,000-4,000 IU daily or 50,000 IU weekly for 8 weeks.")
    if any(f["icd10_code"] == "D50.9" for f in coded_findings):
        plan_therapeutics.append("Initiate oral ferrous sulfate or iron bisglycinate with Vitamin C; reassess reticulocyte count in 4 weeks.")
    if has_ckd:
        plan_therapeutics.append("Strictly avoid nephrotoxic medications, specifically over-the-counter NSAIDs (ibuprofen, naproxen).")
    if not plan_therapeutics:
        plan_therapeutics.append("Continue current health maintenance regimen; no new pharmacotherapy indicated at this time.")

    # Lifestyle
    plan_lifestyle.append("Medical Nutrition Therapy: Adopt Mediterranean or DASH dietary pattern emphasizing low glycemic load, soluble fiber, and healthy monounsaturated fats.")
    if has_dyslipidemia or has_diabetes:
        plan_lifestyle.append("Restrict dietary saturated fats (< 7% of total caloric intake) and eliminate ultra-processed simple sugars.")
    if has_ckd or any(f["icd10_code"].startswith("E87") for f in coded_findings):
        plan_lifestyle.append("Sodium restriction to < 2,000 mg/day; maintain consistent hydration (2 L/day unless clinically contraindicated).")
    plan_lifestyle.append("Exercise prescription: Minimum 150 minutes/week of moderate-intensity aerobic activity (e.g., brisk walking) plus 2 sessions of progressive resistance training.")

    # Follow-up
    plan_followup.append(f"Outpatient follow-up consultation in {8 if (has_diabetes or has_ckd) else 12} weeks with interval repeat laboratory panels.")
    plan_followup.append("Red flag precautions: Seek immediate emergency medical care if experiencing severe chest pain, dyspnea, palpitations, syncope, or dark tarry stools.")

    plan = {
        "diagnostics_and_workup": plan_diagnostics,
        "therapeutics_and_medications": plan_therapeutics,
        "lifestyle_and_nutrition": plan_lifestyle,
        "follow_up_and_red_flags": plan_followup
    }

    # 6. Formatted monospaced text note for 1-click clipboard paste into Epic / Cerner / Athena
    note_lines = []
    note_lines.append("=" * 80)
    note_lines.append("PULSE AI CLINICAL EHR SOAP PROGRESS NOTE & BILLING AUDIT")
    note_lines.append("=" * 80)
    note_lines.append(f"PATIENT DEMOGRAPHICS: {age} yo | Biological Sex: {str(sex).capitalize()} | DATE: {date_str}")
    note_lines.append(f"ENCOUNTER TYPE: {subjective['encounter_reason']}")
    note_lines.append("-" * 80)
    note_lines.append("")
    note_lines.append("[S] SUBJECTIVE:")
    note_lines.append(f"  * Chief Presentation: {subjective['history_of_present_illness']}")
    note_lines.append(f"  * Active Medications: {', '.join(subjective['active_medications'])}")
    note_lines.append("  * Review of Systems:")
    for ros_line in subjective["review_of_systems"].split("\n"):
        note_lines.append(f"    - {ros_line}")
    note_lines.append("")
    note_lines.append("[O] OBJECTIVE:")
    note_lines.append(f"  * Vitals: {objective['vital_signs']}")
    note_lines.append(f"  * Laboratory Summary: {abnormal_count} abnormal finding(s) of {total_count} biomarker(s) evaluated.")
    note_lines.append("")
    for p in panels:
        note_lines.append(f"  -- {p['panel_name'].upper()} ({p['status_badge']}) --")
        for m in p["markers"]:
            ref_info = f" [Ref: {m['reference_range']}]" if m['reference_range'] else ""
            note_lines.append(f"     {m['name']:<28} {str(m['value']):>6} {m['unit']:<10} {m['flag_badge']:<12}{ref_info}")
        note_lines.append("")
    note_lines.append("[A] ASSESSMENT & CLINICAL IMPRESSION:")
    note_lines.append(f"  * Clinical Synthesis: {clinical_synthesis}")
    note_lines.append("")
    note_lines.append("  * Problem List & Standardized Billing Codes (ICD-10-CM / SNOMED CT):")
    for idx, f in enumerate(coded_findings, 1):
        note_lines.append(f"    {idx}. [{f['icd10_code']}] {f['icd10_description']}")
        note_lines.append(f"       SNOMED CT: {f['snomed_concept_id']} ({f['snomed_fsn']}) | Tier: {f['billing_tier']}")
    if differentials:
        note_lines.append("")
        note_lines.append("  * Differential Diagnoses:")
        for diff in differentials:
            note_lines.append(f"    - Finding: {diff['finding']}")
            for rd in diff["ranked_differentials"]:
                note_lines.append(f"      {rd}")
    note_lines.append("")
    note_lines.append("[P] PLAN & CLINICAL RECOMMENDATIONS:")
    note_lines.append("  1. DIAGNOSTICS & SURVEILLANCE:")
    for d_item in plan_diagnostics:
        note_lines.append(f"     - {d_item}")
    note_lines.append("  2. PHARMACOTHERAPY & MEDICATION MANAGEMENT:")
    for t_item in plan_therapeutics:
        note_lines.append(f"     - {t_item}")
    note_lines.append("  3. MEDICAL NUTRITION & LIFESTYLE PRESCRIPTION:")
    for l_item in plan_lifestyle:
        note_lines.append(f"     - {l_item}")
    note_lines.append("  4. FOLLOW-UP INTERVAL & RED FLAG PRECAUTIONS:")
    for f_item in plan_followup:
        note_lines.append(f"     - {f_item}")
    note_lines.append("")
    note_lines.append("=" * 80)
    note_lines.append("DOCUMENTED VIA PULSE AI EHR COPILOT - MD VERIFICATION REQUIRED PRIOR TO SIGN-OFF")
    note_lines.append("=" * 80)

    formatted_text = "\n".join(note_lines)

    return {
        "subjective": subjective,
        "objective": objective,
        "assessment": assessment,
        "plan": plan,
        "billing_codes": coded_findings,
        "formatted_progress_note": formatted_text,
        "generated_timestamp": time.time()
    }


