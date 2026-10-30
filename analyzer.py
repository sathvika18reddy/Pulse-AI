"""Abnormality flagging against reference ranges with sex-adjusted defaults, plausibility checks, and critical escalation."""
import re
import datetime
import kb

def normalize_unit(key: str, val: float, unit: str, rlo: float = None, rhi: float = None):
    """Normalize common foreign units to standard KB units (e.g. mmol/L to mg/dL)."""
    if not unit:
        return val, unit, rlo, rhi
    u = unit.strip().lower()
    
    # Glucose (standard mg/dL)
    if key in ("glucose_f", "glucose_pp", "glucose_r") and "mmol" in u:
        factor = 18.0182
        return round(val * factor, 1), "mg/dL", round(rlo * factor, 1) if rlo is not None else None, round(rhi * factor, 1) if rhi is not None else None
    
    # Lipids: Chol, LDL, HDL (standard mg/dL)
    if key in ("chol", "ldl", "hdl") and "mmol" in u:
        factor = 38.67
        return round(val * factor, 1), "mg/dL", round(rlo * factor, 1) if rlo is not None else None, round(rhi * factor, 1) if rhi is not None else None
        
    # Triglycerides (standard mg/dL)
    if key == "trig" and "mmol" in u:
        factor = 88.57
        return round(val * factor, 1), "mg/dL", round(rlo * factor, 1) if rlo is not None else None, round(rhi * factor, 1) if rhi is not None else None
        
    # Bilirubin (standard mg/dL)
    if "bili" in key and ("umol" in u or "µmol" in u):
        factor = 17.1
        return round(val / factor, 2), "mg/dL", round(rlo / factor, 2) if rlo is not None else None, round(rhi / factor, 2) if rhi is not None else None
        
    # Creatinine (standard mg/dL)
    if key == "creatinine" and ("umol" in u or "µmol" in u):
        factor = 88.4
        return round(val / factor, 2), "mg/dL", round(rlo / factor, 2) if rlo is not None else None, round(rhi / factor, 2) if rhi is not None else None
        
    # Hemoglobin (standard g/dL)
    if key == "hemoglobin" and u == "g/l":
        return round(val / 10.0, 1), "g/dL", round(rlo / 10.0, 1) if rlo is not None else None, round(rhi / 10.0, 1) if rhi is not None else None
        
    # Calcium (standard mg/dL)
    if key == "calcium" and "mmol" in u:
        factor = 4.0
        return round(val * factor, 2), "mg/dL", round(rlo * factor, 2) if rlo is not None else None, round(rhi * factor, 2) if rhi is not None else None

    return val, unit, rlo, rhi

def check_plausibility(key: str, val: float):
    """Check if value falls within absolute human physiological boundaries."""
    if val < 0:
        return False, "Negative values are physiologically impossible."
    bounds = getattr(kb, "PHYSIOLOGICAL_BOUNDS", {}).get(key)
    if bounds:
        min_p, max_p = bounds
        if val < min_p or val > max_p:
            return False, f"Value {val} falls outside human physiological bounds ({min_p} - {max_p}). Likely an OCR misread."
    return True, ""

def check_critical(key: str, val: float):
    """Deterministic check against critical clinical thresholds."""
    crit_dict = getattr(kb, "CRITICAL_THRESHOLDS", {}).get(key, {})
    if "low" in crit_dict:
        thresh, alert_msg = crit_dict["low"]
        if val <= thresh:
            return True, alert_msg
    if "high" in crit_dict:
        thresh, alert_msg = crit_dict["high"]
        if val >= thresh:
            return True, alert_msg
    return False, None

def flag(row: dict, sex: str = None, age: int = None, pregnancy_trimester: int = None, medications: list = None, conditions: list = None) -> dict:
    ref = kb.BY_KEY[row["key"]]
    def_lo, def_hi = kb.get_reference_range(row["key"], sex=sex, pregnancy_trimester=pregnancy_trimester)
    
    # 1. Normalize unit if needed (e.g. mmol/L -> mg/dL)
    orig_val, orig_unit = row.get("value"), row.get("unit")
    v, unit, rlo, rhi = normalize_unit(row["key"], orig_val, orig_unit, row.get("ref_low"), row.get("ref_high"))
    
    # 2. Plausibility bounds check
    plausible, plausibility_err = check_plausibility(row["key"], v)
    
    # 3. Printed reference range always wins over defaults
    lo = rlo if rlo is not None else def_lo
    hi = rhi if rhi is not None or rlo is not None else def_hi
    
    # 4. Status and deviation
    status, dev = "normal", 0.0
    if lo is not None and v < lo and lo > 0:
        status, dev = "low", (lo - v) / lo
    elif hi is not None and v > hi:
        status, dev = "high", (v - hi) / hi if hi > 0 else 1.0
        
    # 5. Critical emergency escalation
    is_critical, critical_alert = check_critical(row["key"], v)
    
    # 6. Severity grading
    if status == "normal":
        sev = "none"
    elif is_critical:
        sev = "marked"
    elif dev < .10:
        sev = "mild"
    elif dev < .30:
        sev = "moderate"
    else:
        sev = "marked"
        
    meaning = ref["high_meaning"] if status == "high" else ref["low_meaning"] if status == "low" else ""
    
    # 7. Visual position percentage for UI range bar (0% = at low, 100% = at high)
    if lo is not None and hi is not None and hi > lo:
        pos = ((v - lo) / (hi - lo)) * 100.0
    elif hi is not None and hi > 0:
        pos = (v / hi) * 100.0
    else:
        pos = 50.0
        
    # 8. Medication-Lab Interaction Check
    med_interaction = None
    if medications:
        med_list = [m.lower().strip() for m in medications if isinstance(m, str)]
        for drug_class, d_info in getattr(kb, "MEDICATION_LAB_INTERACTIONS", {}).items():
            if row["key"] in d_info.get("markers", []):
                for drug_name in d_info.get("names", []):
                    if any(drug_name in med for med in med_list):
                        med_interaction = {
                            "drug_class": drug_class,
                            "matched_name": drug_name,
                            "clinical_effect": d_info.get("effect"),
                            "guideline": d_info.get("guideline")
                        }
                        break
            if med_interaction:
                break

    res = {
        **row,
        "value": v,
        "unit": unit,
        "ref_low": lo,
        "ref_high": hi,
        "status": status,
        "severity": sev,
        "deviation_pct": round(dev * 100, 1),
        "position_pct": round(pos, 1),
        "meaning": meaning,
        "is_critical": is_critical,
        "critical_alert": critical_alert,
        "plausible": plausible,
        "plausibility_error": plausibility_err,
        "loinc": kb.get_loinc(row["key"]),
        "guideline": kb.get_guideline(row.get("category", "")),
        "medication_interaction": med_interaction,
        "pregnancy_adjusted": bool(pregnancy_trimester and row["key"] in getattr(kb, "PREGNANCY_RANGES", {}))
    }
    if orig_val != v or orig_unit != unit:
        res["original_value"] = orig_val
        res["original_unit"] = orig_unit
    return res

def analyze(rows, sex: str = None, age: int = None, pregnancy_trimester: int = None, medications: list = None, conditions: list = None):
    return [flag(r, sex=sex, age=age, pregnancy_trimester=pregnancy_trimester, medications=medications, conditions=conditions) for r in rows]

def analyze_trajectory(history_reports: list[dict]) -> dict:
    """
    Longitudinal Health Trajectory & Velocity Engine:
    Calculates rate of change (velocity d(value)/dt), directional shifts,
    and flags critical clinical progression patterns (e.g. rapid renal decline, progressive anemia).
    """
    if not history_reports or len(history_reports) < 2:
        return {"trajectories": {}, "velocity_alerts": []}
        
    # Sort chronologically by uploaded or date
    sorted_reps = sorted(history_reports, key=lambda r: r.get("uploaded", 0))
    
    # Group results by biomarker key
    marker_series = {}
    for rep in sorted_reps:
        r_date = rep.get("date") or rep.get("filename") or "Unknown"
        r_ts = rep.get("uploaded", 0)
        for row in rep.get("results", []):
            k = row.get("key")
            if not k or row.get("value") is None:
                continue
            marker_series.setdefault(k, []).append({
                "date": r_date,
                "timestamp": r_ts,
                "value": float(row["value"]),
                "status": row.get("status", "normal"),
                "severity": row.get("severity", "none"),
                "unit": row.get("unit", "")
            })
            
    trajectories = {}
    alerts = []
    
    for k, pts in marker_series.items():
        if len(pts) < 2:
            continue
            
        m_info = kb.BY_KEY.get(k, {})
        m_name = m_info.get("name", k)
        first_pt = pts[0]
        latest_pt = pts[-1]
        prior_pt = pts[-2]
        
        # Absolute and percentage delta from immediate prior visit
        delta = round(latest_pt["value"] - prior_pt["value"], 2)
        pct_change = round(((latest_pt["value"] - prior_pt["value"]) / max(abs(prior_pt["value"]), 0.001)) * 100, 1)
        
        # Direction
        if abs(pct_change) < 2.5:
            direction = "stable"
        elif pct_change > 0:
            direction = "rising"
        else:
            direction = "falling"
            
        # Overall trajectory across all visits
        vals = [p["value"] for p in pts]
        is_consistently_dropping = len(vals) >= 3 and all(vals[i] < vals[i-1] for i in range(1, len(vals)))
        is_consistently_rising = len(vals) >= 3 and all(vals[i] > vals[i-1] for i in range(1, len(vals)))
        
        traj_data = {
            "key": k,
            "name": m_name,
            "unit": latest_pt["unit"],
            "points": pts,
            "current_value": latest_pt["value"],
            "prior_value": prior_pt["value"],
            "delta": delta,
            "pct_change": pct_change,
            "direction": direction,
            "point_count": len(pts)
        }
        
        # Alert Pattern 1: Rapid Renal Decline (KDIGO: eGFR decline > 5 mL/min/1.73m2/year)
        if k == "egfr" and len(pts) >= 2:
            time_span_days = max((latest_pt["timestamp"] - first_pt["timestamp"]) / 86400.0, 1.0)
            annualized_loss = (first_pt["value"] - latest_pt["value"]) * (365.25 / time_span_days)
            if annualized_loss >= 5.0 and latest_pt["value"] < first_pt["value"]:
                alerts.append({
                    "key": k,
                    "name": m_name,
                    "alert_type": "rapid_renal_decline",
                    "severity": "high",
                    "title": "Rapid eGFR Renal Decline Detected",
                    "message": f"Filtration rate has declined by {abs(delta)} {latest_pt['unit']} (projected {round(annualized_loss, 1)} mL/min/yr loss). KDIGO guidelines identify decline > 5 mL/min/yr as rapid CKD progression requiring nephrology review.",
                    "guideline": "KDIGO 2024 Clinical Practice Guideline for CKD Evaluation"
                })

        # Alert Pattern 2: Progressive Hemoglobin or Iron Depletion
        if k in ("hemoglobin", "ferritin") and (is_consistently_dropping or (len(pts) >= 2 and pct_change <= -15.0)):
            alerts.append({
                "key": k,
                "name": m_name,
                "alert_type": "progressive_anemia",
                "severity": "moderate" if latest_pt["status"] == "normal" else "high",
                "title": f"Consecutive Downward Trajectory in {m_name}",
                "message": f"{m_name} shows consecutive declining velocity across past tests ({prior_pt['value']} -> {latest_pt['value']} {latest_pt['unit']}, {pct_change}% shift). Indicates progressive unreplenished blood loss or depleted nutritional reserves.",
                "guideline": "WHO Guidelines on the Assessment of Nutritional Anemia"
            })

        # Alert Pattern 3: Escalating Glycemic Risk
        if k in ("glucose_f", "hba1c") and (is_consistently_rising or (len(pts) >= 2 and pct_change >= 15.0 and latest_pt["status"] != "normal")):
            alerts.append({
                "key": k,
                "name": m_name,
                "alert_type": "glycemic_escalation",
                "severity": "moderate" if latest_pt["value"] < 126 else "high",
                "title": f"Upward Glycemic Trajectory in {m_name}",
                "message": f"{m_name} demonstrates accelerating upward trajectory ({prior_pt['value']} -> {latest_pt['value']} {latest_pt['unit']}, +{pct_change}%). Suggests diminishing glycemic control; ADA guidelines recommend reviewing treatment and metabolic habits.",
                "guideline": "ADA Standards of Care in Diabetes (2024)"
            })
            
        trajectories[k] = traj_data

    return {
        "trajectories": trajectories,
        "velocity_alerts": alerts
    }

def parse_date_or_timestamp(date_str: str, timestamp: float = None):
    """Safely parse a human date string or Unix timestamp into a datetime object."""
    if date_str and isinstance(date_str, str):
        date_clean = date_str.strip()
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
            try:
                return datetime.datetime.strptime(date_clean, fmt)
            except Exception:
                continue
    if timestamp:
        try:
            return datetime.datetime.fromtimestamp(float(timestamp))
        except Exception:
            pass
    return None

def compute_report_diff(baseline_report: dict, current_report: dict) -> dict:
    """
    Intelligent Lab Report "Diff" Engine (Visit-over-Visit Treatment Response).

    Performs a comparative clinical delta between two reports:
      - Categorizes markers into Resolved (🟢), Improving (↗️), Stable (⚪), Worsening (↘️), New Alert (🔴)
      - Quantifies absolute change (Δ) and percentage change (%Δ)
      - Computes aggregate Therapeutic Response Score (0-100%) and clinical efficacy tier
      - Identifies newly added or omitted biomarker panels
      - Generates an executive visit-over-visit narrative for clinicians and patients
    """
    # 1. Unpack baseline and current data
    b_res = baseline_report.get("results", []) if isinstance(baseline_report, dict) else (baseline_report or [])
    c_res = current_report.get("results", []) if isinstance(current_report, dict) else (current_report or [])

    b_meta = baseline_report if isinstance(baseline_report, dict) else {}
    c_meta = current_report if isinstance(current_report, dict) else {}

    b_id = b_meta.get("id", "baseline")
    c_id = c_meta.get("id", "current")
    b_date_str = b_meta.get("date") or "Baseline"
    c_date_str = c_meta.get("date") or "Current"
    b_fn = b_meta.get("filename") or "Baseline Report"
    c_fn = c_meta.get("filename") or "Current Report"

    # 2. Compute elapsed time
    dt_base = parse_date_or_timestamp(b_meta.get("date"), b_meta.get("uploaded"))
    dt_curr = parse_date_or_timestamp(c_meta.get("date"), c_meta.get("uploaded"))
    
    elapsed_days = 0
    if dt_base and dt_curr:
        elapsed_days = abs((dt_curr - dt_base).days)
    elif b_meta.get("uploaded") and c_meta.get("uploaded"):
        elapsed_days = int(abs(c_meta["uploaded"] - b_meta["uploaded"]) / 86400.0)

    if elapsed_days >= 30:
        months = round(elapsed_days / 30.4, 1)
        m_str = int(months) if months.is_integer() else months
        elapsed_str = f"{elapsed_days} days (~{m_str} month{'s' if m_str != 1 else ''})"
    elif elapsed_days > 0:
        elapsed_str = f"{elapsed_days} day{'s' if elapsed_days != 1 else ''}"
    else:
        elapsed_str = "Same-day / Follow-up interval"

    # 3. Index by biomarker key
    b_map = {}
    for r in b_res:
        if not isinstance(r, dict):
            continue
        k = r.get("key")
        if not k and r.get("name"):
            res = kb.resolve_marker(r["name"])
            if res:
                k = res[0]
        if k:
            b_map[str(k).lower()] = r

    c_map = {}
    for r in c_res:
        if not isinstance(r, dict):
            continue
        k = r.get("key")
        if not k and r.get("name"):
            res = kb.resolve_marker(r["name"])
            if res:
                k = res[0]
        if k:
            c_map[str(k).lower()] = r

    common_keys = sorted(list(set(b_map.keys()) & set(c_map.keys())))
    added_keys = sorted(list(set(c_map.keys()) - set(b_map.keys())))
    omitted_keys = sorted(list(set(b_map.keys()) - set(c_map.keys())))

    # 4. Process matched biomarkers
    matched_diffs = []
    category_buckets = {}

    for k in common_keys:
        b_row = b_map[k]
        c_row = c_map[k]
        m_info = kb.BY_KEY.get(k, {})
        m_name = c_row.get("name") or b_row.get("name") or m_info.get("name", k.upper())
        cat = c_row.get("category") or b_row.get("category") or m_info.get("category", "General")
        unit = c_row.get("unit") or b_row.get("unit") or ""
        ref_lo = c_row.get("ref_low", b_row.get("ref_low"))
        ref_hi = c_row.get("ref_high", b_row.get("ref_high"))

        b_val = b_row.get("value")
        c_val = c_row.get("value")
        b_status = b_row.get("status", "normal")
        c_status = c_row.get("status", "normal")

        # Numeric delta
        try:
            b_float = float(b_val)
            c_float = float(c_val)
            delta = round(c_float - b_float, 2)
            pct_change = round(((c_float - b_float) / max(abs(b_float), 0.001)) * 100.0, 1)
            daily_rate = round(delta / max(elapsed_days, 1), 4) if elapsed_days > 0 else 0.0
            is_numeric = True
        except (ValueError, TypeError):
            delta = 0.0
            pct_change = 0.0
            daily_rate = 0.0
            is_numeric = False

        # Trajectory Classification
        trajectory = "stable"
        badge = "⚪ Stable"
        note = ""

        # Case 1: Resolved to normal
        if b_status != "normal" and c_status == "normal":
            trajectory = "resolved"
            badge = "🟢 Normalized (Resolved)"
            note = f"Full laboratory resolution: normalized from abnormal baseline ({b_val}) into optimal reference target ({c_val} {unit})."

        # Case 2: Newly abnormal (New Alert)
        elif b_status == "normal" and c_status != "normal":
            trajectory = "new_alert"
            badge = "🔴 Newly Abnormal"
            note = f"Newly emergent abnormal shift: previously normal ({b_val}), now shifted into {c_status} bracket ({c_val} {unit})."

        # Case 3: Baseline abnormal, current still abnormal
        elif b_status != "normal" and c_status != "normal":
            if b_status == "high":
                if delta < 0 and abs(pct_change) >= 2.5:
                    trajectory = "improving"
                    badge = "↗️ Clinically Improving"
                    note = f"Favorable therapeutic reduction towards reference ceiling ({b_val} → {c_val} {unit}, {pct_change}% shift)."
                elif delta > 0 and abs(pct_change) >= 2.5:
                    trajectory = "worsening"
                    badge = "↘️ Worsening Escalation"
                    note = f"Adverse upward drift further exceeding reference upper limit ({b_val} → {c_val} {unit}, +{pct_change}%)."
                else:
                    trajectory = "stable"
                    badge = "⚪ Plateaued Abnormal"
                    note = f"Abnormal baseline has plateaued without significant change ({b_val} → {c_val} {unit}, {pct_change}%)."
            elif b_status == "low":
                if delta > 0 and abs(pct_change) >= 2.5:
                    trajectory = "improving"
                    badge = "↗️ Clinically Improving"
                    note = f"Favorable upward recovery towards normal lower threshold ({b_val} → {c_val} {unit}, +{pct_change}% gain)."
                elif delta < 0 and abs(pct_change) >= 2.5:
                    trajectory = "worsening"
                    badge = "↘️ Worsening Decline"
                    note = f"Adverse downward decline deeper below normal threshold ({b_val} → {c_val} {unit}, {pct_change}%)."
                else:
                    trajectory = "stable"
                    badge = "⚪ Plateaued Abnormal"
                    note = f"Low baseline has plateaued without significant change ({b_val} → {c_val} {unit}, {pct_change}%)."
            else:
                trajectory = "stable"
                badge = "⚪ Stable Abnormal"
                note = f"Remains abnormal with minimal delta ({b_val} → {c_val} {unit})."

        # Case 4: Baseline normal, current normal
        else:
            # Biomarkers where higher is clinically protective (e.g. HDL, eGFR, Vit D, B12)
            if k in ("hdl", "egfr", "vitd", "b12") and pct_change >= 5.0:
                trajectory = "improving"
                badge = "↗️ Positive Gain (Optimal)"
                note = f"Favorable physiological optimization within healthy reference bounds ({b_val} → {c_val} {unit}, +{pct_change}%)."
            # Biomarkers where lower is clinically protective (e.g. LDL, Chol, Trig, Glucose, ESR)
            elif k in ("ldl", "chol", "trig", "glucose_f", "glucose_pp", "esr") and pct_change <= -5.0:
                trajectory = "improving"
                badge = "↗️ Positive Reduction (Optimal)"
                note = f"Favorable physiological optimization within healthy reference bounds ({b_val} → {c_val} {unit}, {pct_change}%)."
            elif abs(pct_change) > 15.0:
                trajectory = "stable"
                badge = "⚪ Fluctuating Normal"
                note = f"Physiological fluctuation within healthy normal reference limits ({b_val} → {c_val} {unit})."
            else:
                trajectory = "stable"
                badge = "⚪ Stable (Normal)"
                note = f"Maintained homeostatic stability within reference limits ({b_val} → {c_val} {unit})."

        item = {
            "key": k,
            "name": m_name,
            "category": cat,
            "unit": unit,
            "baseline_value": b_val,
            "baseline_status": b_status,
            "current_value": c_val,
            "current_status": c_status,
            "ref_low": ref_lo,
            "ref_high": ref_hi,
            "delta": delta,
            "pct_change": pct_change,
            "daily_rate": daily_rate,
            "trajectory": trajectory,
            "trajectory_badge": badge,
            "clinical_note": note
        }
        matched_diffs.append(item)
        category_buckets.setdefault(cat, []).append(item)

    # 5. Process Added & Omitted Markers
    added_markers = []
    for k in added_keys:
        r = c_map[k]
        m_info = kb.BY_KEY.get(k, {})
        added_markers.append({
            "key": k,
            "name": r.get("name") or m_info.get("name", k.upper()),
            "category": r.get("category", "General"),
            "value": r.get("value"),
            "unit": r.get("unit", ""),
            "status": r.get("status", "normal"),
            "ref_low": r.get("ref_low"),
            "ref_high": r.get("ref_high"),
            "note": "Newly ordered in current visit (not measured in baseline visit)."
        })

    omitted_markers = []
    for k in omitted_keys:
        r = b_map[k]
        m_info = kb.BY_KEY.get(k, {})
        omitted_markers.append({
            "key": k,
            "name": r.get("name") or m_info.get("name", k.upper()),
            "category": r.get("category", "General"),
            "baseline_value": r.get("value"),
            "unit": r.get("unit", ""),
            "baseline_status": r.get("status", "normal"),
            "note": "Measured in baseline visit; omitted / not rechecked in current visit."
        })

    # Sort matched_diffs by clinical attention priority
    priority_order = {"new_alert": 0, "worsening": 1, "resolved": 2, "improving": 3, "stable": 4}
    matched_diffs.sort(key=lambda d: (priority_order.get(d["trajectory"], 5), -abs(d.get("pct_change", 0))))

    # 6. Compute Counts & Therapeutic Response Score
    abnormal_base_count = sum(1 for d in matched_diffs if d["baseline_status"] != "normal")
    resolved_count = sum(1 for d in matched_diffs if d["trajectory"] == "resolved")
    improving_count = sum(1 for d in matched_diffs if d["trajectory"] == "improving")
    stable_count = sum(1 for d in matched_diffs if d["trajectory"] == "stable")
    worsening_count = sum(1 for d in matched_diffs if d["trajectory"] == "worsening")
    new_alert_count = sum(1 for d in matched_diffs if d["trajectory"] == "new_alert")

    if abnormal_base_count > 0:
        base_points = (resolved_count * 1.0) + (improving_count * 0.75)
        raw_score = (base_points / abnormal_base_count) * 100.0
        # Penalties for newly abnormal or worsening markers
        penalties = (new_alert_count * 10.0) + (worsening_count * 10.0)
        score = round(max(0.0, min(100.0, raw_score - penalties)), 1)
    else:
        if new_alert_count == 0:
            score = 100.0
        else:
            score = round(max(0.0, 100.0 - (new_alert_count * 20.0)), 1)

    # Therapeutic Tiers
    if score >= 80.0:
        tier_status = "excellent"
        tier_badge = "🌟 Outstanding Therapeutic Response"
        tier_summary = "Targeted biomarkers have demonstrated robust normalization or marked clinical improvement with zero or minimal emergent abnormalities."
    elif score >= 60.0:
        tier_status = "good"
        tier_badge = "📈 Favorable Therapeutic Progress"
        tier_summary = "Positive therapeutic momentum: Meaningful clinical improvements observed across primary target markers, indicating responsive medical and lifestyle therapy."
    elif score >= 40.0:
        tier_status = "partial"
        tier_badge = "⚖️ Mixed / Partial Treatment Response"
        tier_summary = "Mixed therapeutic response: While certain biomarkers have responded favorably, others remain stubbornly abnormal or have plateaued."
    else:
        tier_status = "suboptimal"
        tier_badge = "⚠️ Suboptimal Response / Regimen Review Suggested"
        tier_summary = "Biomarkers have not reached targeted clinical thresholds or new abnormal shifts have emerged. A comprehensive clinical regimen review with your physician is advised."

    # 7. Category Breakdown Summaries
    category_breakdown = []
    for cat, items in category_buckets.items():
        c_resolved = sum(1 for x in items if x["trajectory"] == "resolved")
        c_improving = sum(1 for x in items if x["trajectory"] == "improving")
        c_worsening = sum(1 for x in items if x["trajectory"] == "worsening")
        c_alerts = sum(1 for x in items if x["trajectory"] == "new_alert")
        
        cat_notes = []
        if c_resolved: cat_notes.append(f"{c_resolved} normalized")
        if c_improving: cat_notes.append(f"{c_improving} improving")
        if c_worsening: cat_notes.append(f"{c_worsening} worsening")
        if c_alerts: cat_notes.append(f"{c_alerts} new alert")
        summary_str = ", ".join(cat_notes) if cat_notes else "All markers stable"
        
        category_breakdown.append({
            "category": cat,
            "total_markers": len(items),
            "summary": summary_str,
            "resolved_count": c_resolved,
            "improving_count": c_improving,
            "worsening_count": c_worsening,
            "new_alert_count": c_alerts
        })

    # 8. Executive Narrative
    notable = []
    for d in matched_diffs:
        if d["trajectory"] in ("resolved", "new_alert") or (d["trajectory"] in ("improving", "worsening") and abs(d["pct_change"]) >= 10.0):
            sign = "+" if d["delta"] > 0 else ""
            notable.append(f"{d['name']} ({d['baseline_value']} → {d['current_value']} {d['unit']}, {sign}{d['pct_change']}%)")
    
    notable_str = f"Notable biomarker shifts include: {', '.join(notable[:3])}." if notable else "Biomarkers remained within stable physiological limits."
    
    positive_total = resolved_count + improving_count
    narrative = (
        f"Across {elapsed_str} between visits, {positive_total} of {abnormal_base_count} "
        f"previously abnormal biomarkers demonstrated favorable therapeutic response "
        f"({resolved_count} fully normalized, {improving_count} clinically improving). "
        f"{notable_str} "
        f"Overall Therapeutic Response Score is {score}% ({tier_badge.split(' ', 1)[1] if ' ' in tier_badge else tier_badge})."
    )

    return {
        "baseline": {
            "id": b_id,
            "date": b_date_str,
            "filename": b_fn,
            "total_markers": len(b_res),
            "abnormal_count": sum(1 for r in b_res if r.get("status") != "normal")
        },
        "current": {
            "id": c_id,
            "date": c_date_str,
            "filename": c_fn,
            "total_markers": len(c_res),
            "abnormal_count": sum(1 for r in c_res if r.get("status") != "normal")
        },
        "elapsed_days": elapsed_days,
        "elapsed_str": elapsed_str,
        "therapeutic_response_score": score,
        "therapeutic_tier": tier_status,
        "therapeutic_badge": tier_badge,
        "therapeutic_summary": tier_summary,
        "counts": {
            "total_compared": len(matched_diffs),
            "resolved": resolved_count,
            "improving": improving_count,
            "stable": stable_count,
            "worsening": worsening_count,
            "new_alert": new_alert_count,
            "added_markers": len(added_markers),
            "omitted_markers": len(omitted_markers)
        },
        "differences": matched_diffs,
        "added_markers": added_markers,
        "omitted_markers": omitted_markers,
        "category_breakdown": category_breakdown,
        "narrative": narrative
    }


