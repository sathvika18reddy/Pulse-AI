# Standing instructions for agents working on Pulse AI

Project: AI blood-test report analyzer (OCR -> RAG -> LLM -> tool-using agent), Python/Flask + vanilla JS.

- Keep the module split: ocr.py, analyzer.py, kb.py, rag.py, agent.py, store.py, app.py, static/index.html.
- Never hard-code API keys. Read ANTHROPIC_API_KEY (or GEMINI_API_KEY) from the environment only.
- The report's printed reference range always wins over kb.py defaults.
- The agent must never invent lab values, diagnose, or prescribe; always recommend a doctor for abnormal results.
- Use only synthetic / de-identified sample data. Never commit real patient reports (data/ is git-ignored).
- Python 3.10+, type hints where cheap, small functions, no new dependency without adding it to requirements.txt.
- After any change: run `python -m pytest -q` (if tests exist) and `python make_samples.py && python app.py` smoke test.
