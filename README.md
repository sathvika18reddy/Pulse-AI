# Pulse AI — AI-Powered Blood Test Analyzer

> **Decoding Blood. Instantly.**
> Upload a lab report (PDF or phone photo) → OCR extracts the values → abnormal results are flagged → an AI agent explains them in plain language, in your language, by text or voice, and answers follow-up questions grounded in *your* report.

*Research prototype. Not a medical device. Not medical advice.*

---

## 1. What it does

| Feature | How |
|---|---|
| Read PDF / image reports | Tesseract OCR (`ocr.py`), `pdfplumber` for digital PDFs |
| Flag abnormal values + severity | Rule engine against reference ranges (`analyzer.py`, `kb.py`) |
| Plain-language multilingual summary | LLM (Claude via Anthropic API; Gemini is a drop-in swap, see §9) |
| Report-specific Q&A chatbot | Tool-using agent + RAG (`agent.py`, `rag.py`) |
| Voice in/out | Browser Web Speech API (TTS + STT) |
| Trends across reports | Stored JSON history + Chart.js |

### Architecture (matches the project deck)

```
Report (PDF/img) → OCR Tool → Parser → Analyzer (flags)
                                         │
                        ┌────────────────┴───────────────┐
                        ▼                                ▼
                RAG index (KB + this report        Orchestrator Agent (LLM)
                + earlier reports)  ◄── tools ───► get_report · get_abnormal ·
                                                    lookup_marker · search_context · get_trend
                                                         │
                                          Summary + Chat (text / voice, any language)
```

### Folder layout

```
pulse-ai/
├── app.py            # Flask API + serves the UI
├── ocr.py            # OCR + text → structured rows
├── analyzer.py       # low / normal / high + severity
├── kb.py             # reference ranges + meanings (RAG corpus)
├── rag.py            # TF-IDF retrieval
├── agent.py          # LLM orchestrator, tools, summaries, chat
├── store.py          # JSON storage of past reports
├── make_samples.py   # generates fake sample reports
├── static/index.html # UI
├── AGENTS.md         # standing instructions for Antigravity agents
└── requirements.txt
```

---

## 2. Prerequisites

| Need | Notes |
|---|---|
| **Google Antigravity** | Download from the official Antigravity site, sign in with a personal Google account (preview; Workspace accounts may not be supported yet) |
| **Python 3.10+** | `python --version` |
| **Tesseract OCR** | Windows: UB-Mannheim installer, then add to PATH · macOS: `brew install tesseract poppler` · Ubuntu: `sudo apt install tesseract-ocr poppler-utils` |
| **Poppler** | Only needed for *scanned* PDFs (`pdf2image`) |
| **LLM API key** | Anthropic key for summaries/chat in other languages. *Optional*: without it the app runs with an English-only offline fallback |
| **Chrome or Edge** | Best Web Speech (voice) support |

Verify: `tesseract --version` prints a version.

---

## 3. Quick start (project already provided)

1. Unzip `pulse-ai.zip`.
2. In Antigravity: **File → Open Folder** → select `pulse-ai`.
3. Open the integrated terminal and run:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# optional, enables multilingual LLM summaries + smart chat
# Windows (PowerShell): $env:ANTHROPIC_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-..."

python make_samples.py     # creates sample_report_1.png / _2.png
python app.py              # open http://localhost:5000
```

4. Upload `sample_report_1.png`, then `sample_report_2.png` (so trends appear). Ask: *"Why is my hemoglobin low?"* Switch language to Hindi/Tamil and press 🔊 Listen.

> Windows only: if Tesseract isn't found, add this at the top of `ocr.py`:
> `pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"`

---

## 4. Using Antigravity to build / extend it

Antigravity has two views: the **Editor** (VS Code-style, agent side panel; open with `Cmd/Ctrl+L`) and the **Agent Manager** (mission control where you dispatch agents and review their plans, task lists, walkthroughs and browser recordings).

### 4.1 One-time setup
1. **Open the folder as a workspace** (§3 step 2).
2. **Autonomy level** (setup wizard / Settings): choose **Request Review** or **Agent Decides** while learning. Avoid "Always Proceed" for terminal commands on a project handling health data.
3. **Standing instructions:** the included `AGENTS.md` is read by agents in this workspace. You can also add Rules/Workflows from the Customizations panel (menu names change between versions; look for *Rules* and *Workflows*).
4. **Security:** keep the terminal command policy on review, and restrict the browser sub-agent to `localhost`.
5. **Secrets:** put keys in a `.env`/shell variable, never in prompts or code (`.gitignore` already excludes `.env`).

### 4.2 Recommended workflow: one agent task per phase
Open the Agent Manager, start a conversation in this workspace, and paste the prompts below **one at a time**. Review the **Implementation Plan** artifact before approving, and check the **Walkthrough** afterwards.

**Phase 0: understand**
```
Read AGENTS.md and every .py file. Summarize the architecture in 10 lines and list any bugs, missing error handling, or security issues. Don't change files yet.
```

**Phase 1: run and verify the baseline**
```
Create a venv, install requirements.txt, run make_samples.py, start app.py, then use the browser to open http://localhost:5000, upload sample_report_1.png and sample_report_2.png, and confirm results table, summary and trend charts render. Report screenshots and any errors.
```

**Phase 2: tests**
```
Add pytest tests: (a) ocr.parse_text on 10 sample lines incl. "< 200" and ranges with en-dash; (b) analyzer.flag boundary cases; (c) rag.retrieve returns the matching marker; (d) /api/upload rejects non-PDF/image files. Make them pass.
```

**Phase 3: evaluation (backs the deck's 95 / 90 / 85 % objectives)**
```
Create eval/ with a script that generates 30 synthetic reports (varied fonts, rotation, noise, blur) with ground-truth JSON, runs the pipeline, and prints: field-level OCR accuracy, abnormal-flag precision/recall, and chat grounding accuracy on 20 Q&A pairs. Write results to eval/RESULTS.md.
```

**Phase 4: better OCR for phone photos**
```
Add an optional EasyOCR backend selectable via OCR_ENGINE=easyocr|tesseract, plus deskew and denoise preprocessing. Compare accuracy with the eval script and keep the better default.
```

**Phase 5: more biomarkers + age/sex ranges**
```
Extend kb.py to ~50 markers (full CBC, LFT, KFT, electrolytes, iron studies) and add optional sex/age fields on upload that select the right reference range. Keep the report's printed range as top priority.
```

**Phase 6: semantic RAG**
```
Replace TF-IDF in rag.py with embeddings stored in a local vector store (Chroma or FAISS). Keep the same retrieve() signature. Add a test.
```

**Phase 7: hardening**
```
Add request size/type limits, delete uploaded files after OCR, per-session report access (no listing other users' reports), a visible disclaimer banner, and a basic rate limit. Update README.
```

> Tip: you can run phases 2, 3 and 5 as **parallel agents** in Manager view; they touch mostly different files. Merge one at a time.

### 4.3 Rebuilding from scratch (alternative)
If you want Antigravity to generate the project itself, start an empty folder, copy in `AGENTS.md`, and use this prompt:

```
Build "Pulse AI", a Flask web app: upload a blood report (PDF/image) → Tesseract OCR → parse biomarker/value/unit/reference range → flag low/normal/high with severity → LLM-written plain-language summary in a selectable language (English, Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi) → chat assistant implemented as a tool-calling agent with tools get_report, get_abnormal, lookup_marker, search_context (RAG over a biomarker knowledge base + this report + earlier reports), get_trend → browser voice (Web Speech TTS/STT) → Chart.js trend view across uploaded reports. Follow AGENTS.md. Modules: app.py, ocr.py, analyzer.py, kb.py, rag.py, agent.py, store.py, static/index.html. Include an offline fallback when no API key exists, make_samples.py for synthetic reports, tests, and a README. Produce an implementation plan first.
```

---

## 5. API Reference

| Method | Route | Body / Query | Description |
|---|---|---|---|
| POST | `/api/upload` | multipart `file`, `lang`, `session_id`, `sex`, `age`, `medications` | Dual-path consensus extraction, LOINC binding, SBAR brief, cardiometabolic indices |
| POST | `/api/confirm/<id>` | `{results, sex, age, lang, session_id}` | Human confirmation step: re-analyzes modified values |
| GET / POST | `/api/profile` | `{medications, conditions, pregnancy_trimester, sex, age}` | Persistent patient clinical context & drug interaction checking |
| GET | `/api/timeline` | `?session_id=` | Longitudinal trajectory, statistical velocity $d(val)/dt$, and progression alert flags |
| GET | `/api/fhir/<id>` | `?session_id=` | Standardized HL7 FHIR R4 DiagnosticReport Bundle export (LOINC & UCUM compliant) |
| POST | `/api/fhir/import` | FHIR R4 Bundle JSON | Direct digital ingestion of lab partner feeds bypassing OCR |
| GET / POST | `/api/reminder/<id>` | `{appointment_date, appointment_time, doctor_name, notes}` | RFC 5545 `.ics` iCalendar appointment file with doctor talking points |
| GET | `/api/sbar/<id>` | `?session_id=` | Official Mayo Clinic / Johns Hopkins style SBAR Clinical Handoff Brief |
| POST | `/api/simulate/<id>` | `{interventions}` | Dynamic "What-If" Metabolic Simulator projecting lifestyle & pharmacological shifts |
| POST | `/api/rehearse/<id>` | `{step, user_input, history}` | Interactive Doctor-Patient Consultation Rehearsal Simulator |
| POST | `/api/summary/<id>` | `{lang, session_id}` | Physician-style clinical synthesis & speech script |
| POST | `/api/chat/<id>` | `{question, history, lang}` | Grounded Q&A chatbot with CriticAgent auditor |
| POST | `/api/chat/<id>/stream` | `{question, history, lang}` | Real-time Server-Sent Events (SSE) typewriter streaming Q&A |
| GET | `/api/trends` | `?session_id=` | Biomarker points across historical reports for Chart.js |
| GET | `/api/export/<id>` | `?session_id=` | Printable HTML / PDF clinical summary view |
| POST | `/api/feedback` | `{rating, comment}` | Clinician audit and continuous improvement logging |

---

## 6. Enterprise Clinical Architecture & Unique Features

### 6.1 Unique Feature 1: Dynamic Biomarker Interplay Engine & "What-If" Health Twin
Biomarkers never exist in isolation. Pulse AI features a dynamic cross-marker pathophysiological simulator:
- **Cardiometabolic Indices**: Computes the **TyG (Triglyceride-Glucose) Index** for subclinical insulin resistance, the **Atherogenic Index of Plasma (AIP)** for small-dense LDL vascular plaque vulnerability, and calculated **eGFR (2021 CKD-EPI equation)**.
- **Cross-Marker Syndrome Detection**: Automatically identifies multi-marker patterns such as the *Metabolic Syndrome Triad* (Fasting Glucose + HbA1c + Triglycerides + low HDL), *Atherogenic Lipid Axis*, *Renal Hemodynamic Axis*, and *Microcytic Anemia Axis*.
- **Interactive "What-If" Simulation**: Patients adjust evidence-based clinical levers (weight reduction, 150 min/wk exercise, Mediterranean nutrition, statin therapy, iron therapy) to project quantitative biomarker deltas grounded in published clinical trials (Look AHEAD, DPP, PREDIMED, ACCORD, WHO).

### 6.2 Unique Feature 2: Mayo Clinic / Johns Hopkins SBAR Clinical Brief
Transforms raw lab sheets into an executive 1-page clinical handoff document following hospital gold standards:
- **S (Situation)**: Primary lab anomalies, severity grading, critical threshold alerts.
- **B (Background)**: Patient demographics, active medications, drug-lab interactions, longitudinal velocity.
- **A (Assessment)**: Evidence-based pathophysiological mechanisms cited from official guidelines (ADA 2024, KDIGO 2024, AHA/ACC 2019).
- **R (Recommendation)**: Top medical specialist to consult, recommended confirmatory diagnostic follow-up batteries, and prioritized doctor talking points.

### 6.3 Unique Feature 3: Interactive Doctor-Patient Consultation Rehearsal Simulator
Patients frequently feel rushed or anxious during clinical appointments. Pulse AI simulates the exact 4-stage triage interview an endocrinologist or physician will conduct:
1. Clarifying symptom onset, duration, and functional impact.
2. Inquiring regarding medication adherence and OTC supplements.
3. Establishing hereditary and family background.
4. Providing real-time communication coaching to empower the patient to communicate clearly and concisely.

### 6.4 Tri-Persona Interface
- **Patient Experience Mode**: Empathetic plain-language clinical synthesis, speech narration, interactive range bar cards, "What-If" simulation, and doctor rehearsal.
- **Clinician Workspace Mode**: High-density audit grid with official LOINC codes, reference ranges, VLM vs OCR consensus diff, clinical guideline citations, and one-click SBAR handoff export.
- **Community Health Worker (ASHA) Mode**: High-contrast, large-button rapid screening view with instant Green/Amber/Red traffic-light triage and simplified voice guidance in 8 regional languages.

### 6.5 HL7 FHIR R4 & iCalendar RFC 5545 Interoperability
- Export compliant HL7 FHIR R4 bundles (`Patient`, `Observation` with official LOINC codes and UCUM units, `DiagnosticReport`).
- Direct digital ingestion of lab partner FHIR JSON feeds without OCR.
- Generates RFC 5545 `.ics` appointment reminders pre-populated with clinical talking points and alert alarms.

---

## 7. Testing & Clinical Quality Benchmark

Run all 48 test suites:
```bash
python -m pytest -q
# 48 passed in ~1.3s
```

Run clinical evaluation harness:
```bash
python eval/evaluate.py
# OCR Field Extraction Accuracy: 100.0% (Target >= 95.0%)
# Abnormality Flagging Accuracy: 100.0% (Target >= 90.0%)
# Chat Grounding Rate: 100.0% (Target >= 85.0%)
```

---

## 6. Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | unset | Enables LLM summaries/chat; unset → offline English fallback |
| `PULSE_MODEL` | `claude-sonnet-5-5` | LLM model name |

---

## 7. Testing checklist

- [ ] `tesseract --version` works
- [ ] Sample report upload shows 8 rows with correct flags (low Hb, high glucose, low Vit D…)
- [ ] Second upload produces trend charts
- [ ] Language switch changes the summary (needs API key)
- [ ] 🔊 Listen reads the summary; 🎤 captures a question (Chrome/Edge)
- [ ] Chat answer mentions only values present in the report
- [ ] A random non-lab image returns a friendly error (HTTP 422)

---

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| `TesseractNotFoundError` | Install Tesseract and add to PATH / set `tesseract_cmd` (see §3) |
| Scanned PDF fails | Install Poppler and add to PATH |
| "Couldn't find any known lab values" | Use a straighter, higher-resolution image; add the missing marker alias in `kb.py` |
| Summary stays English | `ANTHROPIC_API_KEY` not set in the terminal Flask runs in |
| No voice in your language | Install the OS voice pack; use Chrome/Edge |
| Agent edits too much | Switch to Request Review mode; reference `AGENTS.md` in the prompt |
| Port 5000 busy (macOS AirPlay) | Change `port=` in `app.py` to 5001 |

---

## 9. Using Gemini instead of Claude (Antigravity-native)

`agent.py` isolates all LLM calls in `_client()`, `summarize()` and `chat()`. Prompt Antigravity:

```
Add a provider switch LLM_PROVIDER=anthropic|gemini in agent.py using the google-genai SDK with function calling for the same five tools. Keep the offline fallback. Add tests with a mocked client.
```

---

## 10. Privacy & safety

- Use **synthetic or de-identified** reports only; `data/` is git-ignored.
- The assistant explains, it does not diagnose or prescribe; marked abnormalities prompt a "see a doctor" message.
- Reports sent to an LLM API leave your machine, so review the provider's data policy before using real data.
- For deployment: HTTPS, authentication, encryption at rest, and consent flows are required.

## 11. Roadmap

Evaluation report · EasyOCR/PaddleOCR · vector DB RAG · more markers & age/sex ranges · user accounts · PDF export of the explained report · mobile (PWA) packaging.

## 12. Literature basis

OCR-based lab-report digitization (Alansari et al., 2024; Peking Univ. First Hospital, 2023), ML on extracted labs (Springer IHT, 2025), NLP for abnormal-event capture (hypoglycemia review, 2022), smartphone biomarker screening (Mannino et al., 2018). See the project deck for the full gap analysis.
