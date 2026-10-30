"""RAG: TF-IDF retrieval over (a) the biomarker knowledge base, (b) this report, (c) prior reports."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import kb, store

def _docs(report):
    docs = []
    for m in kb.KB:   # knowledge base
        docs.append(("kb", m["key"], f'{m["name"]} ({m["category"]}) normal {m["low"]}-{m["high"]} {m["unit"]}. '
                     f'High: {m["high_meaning"]} Low: {m["low_meaning"]}'))
    for r in report["results"]:   # current report
        docs.append(("report", r["key"], f'{r["name"]} measured {r["value"]} {r["unit"]}, status {r["status"]} '
                     f'({r["severity"]}), reference {r["ref_low"]}-{r["ref_high"]}. {r["meaning"]}'))
    for p in store.all_reports():  # prior reports
        if report.get("id") and p.get("id") == report.get("id"): continue
        for r in p["results"]:
            docs.append(("history", r["key"], f'Earlier report {p.get("date") or p["filename"]}: {r["name"]} was '
                         f'{r["value"]} {r["unit"]} ({r["status"]}).'))
    return docs

def retrieve(report, query, k=5):
    docs = _docs(report)
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit([d[2] for d in docs] + [query])
    sims = cosine_similarity(vec.transform([query]), vec.transform([d[2] for d in docs]))[0]
    top = sims.argsort()[::-1][:k]
    return [dict(source=docs[i][0], key=docs[i][1], text=docs[i][2]) for i in top if sims[i] > 0]
