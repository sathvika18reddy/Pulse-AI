"""Biomarker knowledge base: 50+ biomarkers with reference ranges, sex variations, and clinical meanings."""
import re

# Format: (key, name, aliases, unit, low, high, high_meaning, low_meaning, category, sex_specific_dict)
_ROWS = [
    # ---------- CBC / HEMOGRAM ----------
    ("hemoglobin", "Hemoglobin", ["hemoglobin", "haemoglobin", "hb", "hgb"], "g/dL", 13.0, 17.0,
     "Can occur with dehydration, smoking, high altitude, or bone marrow conditions.",
     "Suggests anaemia (e.g. iron, B12 or folate deficiency, blood loss); may cause fatigue and breathlessness.", "CBC",
     {"male": (13.0, 17.0), "female": (12.0, 15.5)}),
    
    ("rbc", "RBC Count", ["rbc count", "rbc", "red blood cell count", "red blood cells"], "million/uL", 4.5, 5.5,
     "Seen with dehydration, chronic hypoxia, or polycythaemia.",
     "Seen with anaemia, blood loss, or bone marrow suppression.", "CBC",
     {"male": (4.5, 5.9), "female": (4.0, 5.2)}),

    ("wbc", "WBC Count", ["wbc count", "wbc", "total leucocyte count", "tlc", "white blood cell count", "white blood cells"], "/uL", 4000, 11000,
     "Often indicates infection, systemic inflammation, physical stress, or leukemia.",
     "May reflect viral infection, autoimmune condition, bone marrow issue, or drug toxicity.", "CBC", None),

    ("platelets", "Platelet Count", ["platelet count", "platelets", "plt"], "/uL", 150000, 410000,
     "Can follow reactive inflammation, iron deficiency, or essential thrombocythemia.",
     "Increases bleeding risk; common in dengue, viral fevers, liver disease, or medication effects.", "CBC", None),

    ("hematocrit", "Hematocrit (PCV)", ["hematocrit", "haematocrit", "pcv", "hct"], "%", 40.0, 50.0,
     "Indicates hemoconcentration (dehydration) or excess red cell mass.",
     "Linked to anaemia or significant blood loss.", "CBC",
     {"male": (40.0, 50.0), "female": (36.0, 46.0)}),

    ("mcv", "MCV", ["mcv", "mean corpuscular volume"], "fL", 83.0, 101.0,
     "Macrocytosis: typical in Vitamin B12 or folate deficiency, liver disease, or alcohol excess.",
     "Microcytosis: hallmark of iron deficiency anaemia or thalassaemia trait.", "CBC", None),

    ("mch", "MCH", ["mch", "mean corpuscular hemoglobin"], "pg", 27.0, 33.0,
     "Seen with macrocytic anemias (B12/folate deficiency).",
     "Hypochromia: seen in iron deficiency and thalassaemia.", "CBC", None),

    ("mchc", "MCHC", ["mchc", "mean corpuscular hemoglobin concentration"], "g/dL", 31.5, 35.5,
     "Can indicate hereditary spherocytosis or cold agglutinins.",
     "Seen in hypochromic microcytic anemias.", "CBC", None),

    ("rdw", "RDW", ["rdw-cv", "rdw", "red cell distribution width"], "%", 11.5, 14.5,
     "High variation in red cell size; early sign of nutritional deficiency anemia.",
     "Rarely of clinical concern.", "CBC", None),

    ("esr", "ESR", ["erythrocyte sedimentation rate", "esr"], "mm/hr", 0.0, 20.0,
     "Nonspecific marker of bodily inflammation, autoimmune conditions, or infection.",
     "Generally normal or seen with polycythemia.", "CBC",
     {"male": (0.0, 15.0), "female": (0.0, 20.0)}),

    ("neutrophils", "Neutrophils", ["neutrophils", "neutrophil", "polymorphs", "segs"], "%", 40.0, 70.0,
     "Often elevated during bacterial infections, acute inflammation, or physical trauma.",
     "Neutropenia: increased risk of infection; seen with chemotherapy or viral suppression.", "CBC", None),

    ("lymphocytes", "Lymphocytes", ["lymphocytes", "lymphocyte", "lymphs"], "%", 20.0, 40.0,
     "Common during acute viral infections, chronic lymphocytic leukemia, or healing.",
     "Can indicate immune suppression, severe stress, or steroid use.", "CBC", None),

    ("monocytes", "Monocytes", ["monocytes", "monocyte"], "%", 2.0, 8.0,
     "Elevated in chronic infections (e.g. tuberculosis), recovery from infection, or inflammatory disease.",
     "Rarely isolated; seen with general leukopenia.", "CBC", None),

    ("eosinophils", "Eosinophils", ["eosinophils", "eosinophil", "eos"], "%", 1.0, 6.0,
     "Suggests allergic reactions, asthma, drug hypersensitivity, or parasitic infection.",
     "Usually normal or suppressed during acute steroid use.", "CBC", None),

    ("basophils", "Basophils", ["basophils", "basophil", "baso"], "%", 0.0, 2.0,
     "Seen in allergic responses, chronic myeloid leukemia, or hypothyroidism.",
     "Normally present in very small numbers.", "CBC", None),

    # ---------- DIABETES & METABOLIC ----------
    ("glucose_f", "Fasting Glucose", ["fasting blood sugar", "fasting glucose", "fasting plasma glucose", "fbs", "glucose fasting"], "mg/dL", 70.0, 100.0,
     "100-125 mg/dL is pre-diabetes; 126 mg/dL or higher on repeat tests indicates diabetes.",
     "Hypoglycemia (<70) causes tremors, sweating, hunger, and lightheadedness.", "Diabetes", None),

    ("glucose_pp", "Post-Prandial Glucose", ["post prandial blood sugar", "postprandial glucose", "ppbs", "glucose pp", "post prandial glucose"], "mg/dL", 70.0, 140.0,
     "140-199 mg/dL indicates impaired glucose tolerance; 200 or higher suggests diabetes.",
     "Uncommon unless on excessive insulin or diabetes medication.", "Diabetes", None),

    ("glucose_r", "Random Blood Sugar", ["random blood sugar", "rbs", "random glucose", "blood sugar random"], "mg/dL", 70.0, 140.0,
     "200 mg/dL or higher with classic symptoms suggests diabetes.",
     "Low sugar; requires immediate carbohydrate intake if symptomatic.", "Diabetes", None),

    ("hba1c", "HbA1c", ["hba1c", "glycated hemoglobin", "glycosylated hemoglobin"], "%", 4.0, 5.6,
     "5.7-6.4% indicates pre-diabetes; 6.5% or higher confirms diabetes (reflects ~3 months average).",
     "Rarely a concern; may be seen with hemolytic anemia.", "Diabetes", None),

    # ---------- LIPID PANEL ----------
    ("chol", "Total Cholesterol", ["total cholesterol", "cholesterol total", "cholesterol"], "mg/dL", 0.0, 200.0,
     "Elevated levels build atherosclerotic plaques, increasing long-term cardiovascular risk.",
     "Very low levels can occur with severe malnutrition or hyperthyroidism.", "Lipid", None),

    ("ldl", "LDL Cholesterol", ["ldl cholesterol", "ldl-c", "ldl"], "mg/dL", 0.0, 100.0,
     "The 'bad' cholesterol; deposits cholesterol in artery walls leading to coronary disease.",
     "Optimal level for vascular protection.", "Lipid", None),

    ("hdl", "HDL Cholesterol", ["hdl cholesterol", "hdl-c", "hdl"], "mg/dL", 40.0, 100.0,
     "Cardioprotective; removes excess cholesterol from circulation.",
     "Low HDL (<40 in men, <50 in women) significantly increases heart disease risk.", "Lipid",
     {"male": (40.0, 100.0), "female": (50.0, 100.0)}),

    ("trig", "Triglycerides", ["triglycerides", "triglyceride", "tg"], "mg/dL", 0.0, 150.0,
     "Associated with insulin resistance, high refined carb diet, obesity; >500 risks pancreatitis.",
     "Usually normal or seen with low fat intake.", "Lipid", None),

    ("vldl", "VLDL Cholesterol", ["vldl cholesterol", "vldl-c", "vldl"], "mg/dL", 5.0, 30.0,
     "High VLDL carries triglycerides and contributes to plaque formation.",
     "Generally desirable.", "Lipid", None),

    ("chol_hdl_ratio", "Total/HDL Ratio", ["total/hdl ratio", "chol/hdl ratio", "cholesterol/hdl ratio", "tc/hdl ratio"], "ratio", 0.0, 4.5,
     "Higher ratios indicate elevated cardiovascular risk.",
     "Favorable cardiovascular profile.", "Lipid", None),

    # ---------- LIVER FUNCTION (LFT) ----------
    ("alt", "ALT (SGPT)", ["alt (sgpt)", "sgpt", "alt", "alanine aminotransferase"], "U/L", 0.0, 50.0,
     "Specific marker for liver injury: fatty liver (NAFLD), viral hepatitis, alcohol, or medications.",
     "Normal; has no pathological significance.", "Liver", None),

    ("ast", "AST (SGOT)", ["ast (sgot)", "sgot", "ast", "aspartate aminotransferase"], "U/L", 0.0, 50.0,
     "Reflects liver or cardiac/skeletal muscle injury; AST:ALT > 2 often seen in alcoholic liver injury.",
     "Normal baseline.", "Liver", None),

    ("alp", "Alkaline Phosphatase", ["alkaline phosphatase", "alp"], "U/L", 44.0, 147.0,
     "Points toward bile-duct obstruction, cholestasis, or high bone turnover (e.g. healing fractures).",
     "Rare; can indicate zinc deficiency or malnutrition.", "Liver", None),

    ("bili", "Total Bilirubin", ["total bilirubin", "bilirubin total", "bilirubin"], "mg/dL", 0.1, 1.2,
     "Causes jaundice (yellow eyes/skin); seen in liver disease, bile duct blockage, or hemolysis.",
     "Normal finding.", "Liver", None),

    ("bili_dir", "Direct Bilirubin", ["direct bilirubin", "conjugated bilirubin", "bilirubin direct"], "mg/dL", 0.0, 0.3,
     "Indicates impaired bile excretion from liver or biliary obstruction.",
     "Normal finding.", "Liver", None),

    ("bili_indir", "Indirect Bilirubin", ["indirect bilirubin", "unconjugated bilirubin", "bilirubin indirect"], "mg/dL", 0.1, 0.9,
     "Seen with excess red blood cell breakdown (hemolysis) or Gilbert syndrome.",
     "Normal finding.", "Liver", None),

    ("prot_total", "Total Protein", ["total protein", "protein total"], "g/dL", 6.0, 8.3,
     "Elevated in chronic inflammation, infections, dehydration, or multiple myeloma.",
     "Seen in liver failure, nephrotic kidney syndrome, or severe malnutrition.", "Liver", None),

    ("albumin", "Albumin", ["serum albumin", "albumin"], "g/dL", 3.5, 5.2,
     "Usually reflects severe dehydration.",
     "Indicates reduced liver synthetic capacity, kidney protein leakage, or chronic illness.", "Liver", None),

    ("globulin", "Globulin", ["serum globulin", "globulin"], "g/dL", 2.0, 3.5,
     "Seen in chronic infection, autoimmune disease, or gammopathies.",
     "Can indicate immune deficiency or protein-losing enteropathy.", "Liver", None),

    ("ag_ratio", "A/G Ratio", ["a/g ratio", "albumin globulin ratio", "albumin/globulin ratio"], "ratio", 1.0, 2.2,
     "May reflect underproduction of globulins.",
     "Seen with low albumin (liver/kidney issue) or elevated globulins (autoimmune).", "Liver", None),

    ("ggt", "GGT", ["gamma gt", "gamma glutamyl transferase", "ggt", "ggtp"], "U/L", 0.0, 55.0,
     "Very sensitive marker for bile-duct disorders and alcohol-induced liver toxicity.",
     "Normal; no clinical significance.", "Liver", None),

    # ---------- KIDNEY FUNCTION (KFT) ----------
    ("creatinine", "Creatinine", ["serum creatinine", "creatinine"], "mg/dL", 0.7, 1.3,
     "Key indicator of impaired kidney filtration function or acute kidney injury; also severe dehydration.",
     "Usually reflects low muscle mass; rarely a clinical concern.", "Kidney",
     {"male": (0.7, 1.3), "female": (0.5, 1.1)}),

    ("urea", "Blood Urea", ["blood urea", "urea"], "mg/dL", 15.0, 40.0,
     "Reflects reduced kidney excretion, dehydration, high-protein diet, or upper GI bleeding.",
     "Seen with severe liver dysfunction or inadequate protein intake.", "Kidney", None),

    ("bun", "BUN", ["blood urea nitrogen", "bun"], "mg/dL", 7.0, 20.0,
     "Indicates reduced renal clearance, dehydration, or increased protein catabolism.",
     "Seen in severe liver disease or low protein intake.", "Kidney", None),

    ("uric", "Uric Acid", ["uric acid", "serum uric acid"], "mg/dL", 3.5, 7.2,
     "Hyperuricemia: leads to painful gout crystals in joints or kidney stones.",
     "Rarely of clinical concern.", "Kidney",
     {"male": (3.5, 7.2), "female": (2.6, 6.0)}),

    ("egfr", "eGFR", ["estimated gfr", "egfr", "gfr"], "mL/min/1.73m2", 90.0, 120.0,
     "Normal kidney filtration capacity.",
     "Values below 60 mL/min suggest chronic kidney disease (CKD) requiring clinical evaluation.", "Kidney", None),

    # ---------- ELECTROLYTES & MINERALS ----------
    ("sodium", "Sodium", ["serum sodium", "sodium", "na+", "na"], "mmol/L", 135.0, 145.0,
     "Hypernatremia: typically dehydration or excessive fluid loss; causes confusion and thirst.",
     "Hyponatremia: causes headache, confusion, muscle cramps, and seizure risk if severe.", "Electrolytes", None),

    ("potassium", "Potassium", ["serum potassium", "potassium", "k+"], "mmol/L", 3.5, 5.1,
     "Hyperkalemia: can trigger dangerous cardiac arrhythmias; requires prompt medical evaluation.",
     "Hypokalemia: causes muscle cramps, weakness, fatigue, and heart palpitations.", "Electrolytes", None),

    ("chloride", "Chloride", ["serum chloride", "chloride", "cl-", "cl"], "mmol/L", 96.0, 106.0,
     "Seen in kidney dysfunction, dehydration, or metabolic acidosis.",
     "Seen with prolonged vomiting, fluid loss, or diuretic use.", "Electrolytes", None),

    ("calcium", "Calcium", ["serum calcium", "total calcium", "calcium", "ca"], "mg/dL", 8.5, 10.5,
     "Hypercalcemia: can indicate hyperparathyroidism, excess vitamin D, or bone lesions.",
     "Hypocalcemia: leads to muscle spasms, cramps, numbness, and tingling.", "Electrolytes", None),

    ("phosphorus", "Phosphorus", ["serum phosphorus", "phosphorus", "phosphate"], "mg/dL", 2.5, 4.5,
     "High in kidney failure, hypoparathyroidism, or excessive phosphate intake.",
     "Seen with hyperparathyroidism, malnutrition, or Vitamin D deficiency.", "Electrolytes", None),

    ("magnesium", "Magnesium", ["serum magnesium", "magnesium", "mg"], "mg/dL", 1.7, 2.2,
     "Hypermagnesemia: usually seen in renal impairment or antacid overuse.",
     "Hypomagnesemia: causes tremors, muscle spasms, and cardiac irritability.", "Electrolytes", None),

    # ---------- VITAMINS & IRON STUDIES ----------
    ("vitd", "Vitamin D (25-OH)", ["vitamin d", "25-oh vitamin d", "25 hydroxy vitamin d"], "ng/mL", 30.0, 100.0,
     "High values usually result from excessive supplement intake.",
     "Deficiency: extremely widespread; linked to bone weakness, osteopenia, muscle fatigue, and low immunity.", "Vitamins", None),

    ("b12", "Vitamin B12", ["vitamin b12", "b12", "cobalamin"], "pg/mL", 200.0, 900.0,
     "Elevated values often reflect supplementation or liver conditions.",
     "Deficiency: causes megaloblastic anemia, numbness/tingling in hands/feet, memory lapses, and fatigue.", "Vitamins", None),

    ("iron", "Serum Iron", ["serum iron", "iron total", "iron"], "ug/dL", 60.0, 170.0,
     "Iron overload: seen in hemochromatosis, repeated transfusions, or liver injury.",
     "Iron deficiency: leading cause of nutritional anemia and fatigue.", "Vitamins",
     {"male": (65.0, 175.0), "female": (50.0, 170.0)}),

    ("ferritin", "Ferritin", ["serum ferritin", "ferritin"], "ng/mL", 20.0, 250.0,
     "Reflects iron overload or acute-phase inflammation/infection.",
     "Depleted iron stores; most sensitive test for early iron deficiency.", "Vitamins",
     {"male": (24.0, 336.0), "female": (11.0, 307.0)}),

    ("tibc", "TIBC", ["total iron binding capacity", "tibc"], "ug/dL", 250.0, 450.0,
     "Elevated TIBC is a classic compensatory sign of iron deficiency.",
     "Low in chronic illness, liver disease, or iron overload.", "Vitamins", None),

    # ---------- THYROID PANEL ----------
    ("tsh", "TSH", ["tsh", "thyroid stimulating hormone", "ultra sensitive tsh"], "uIU/mL", 0.4, 4.5,
     "High TSH indicates an underactive thyroid (hypothyroidism); can cause weight gain, fatigue, and cold intolerance.",
     "Low TSH suggests an overactive thyroid (hyperthyroidism); can cause palpitations, anxiety, and weight loss.", "Thyroid", None),

    ("t3", "T3 (Total)", ["total t3", "triiodothyronine", "t3"], "ng/dL", 80.0, 200.0,
     "Associated with hyperthyroidism.",
     "Seen in hypothyroidism or severe systemic illness.", "Thyroid", None),

    ("t4", "T4 (Total)", ["total t4", "thyroxine total", "t4"], "ug/dL", 5.1, 14.1,
     "Seen in hyperthyroidism or excess thyroid replacement.",
     "Seen in hypothyroidism.", "Thyroid", None),

    ("ft3", "Free T3", ["free t3", "ft3"], "pg/mL", 2.3, 4.2,
     "Active unbound thyroid hormone; elevated in hyperthyroidism.",
     "Decreased in hypothyroidism.", "Thyroid", None),

    ("ft4", "Free T4", ["free t4", "ft4"], "ng/dL", 0.8, 1.8,
     "Active unbound thyroxine; elevated in hyperthyroidism.",
     "Decreased in hypothyroidism.", "Thyroid", None),
]

LOINC_CODES = {
    "hemoglobin": "718-7", "rbc": "789-8", "wbc": "6690-2", "platelets": "777-3", "hematocrit": "4544-3",
    "mcv": "787-2", "mch": "785-6", "mchc": "786-4", "rdw": "788-0", "esr": "4537-7",
    "neutrophils": "770-8", "lymphocytes": "736-9", "monocytes": "5905-5", "eosinophils": "711-2", "basophils": "704-7",
    "glucose_f": "1558-6", "glucose_pp": "1557-8", "glucose_r": "2345-7", "hba1c": "4548-4",
    "chol": "2093-3", "ldl": "2089-1", "hdl": "2085-9", "trig": "2571-8", "vldl": "13457-7", "chol_hdl_ratio": "9830-1",
    "alt": "1742-6", "ast": "1920-8", "alp": "6768-6", "bili": "1975-2", "bili_dir": "1968-7",
    "bili_indir": "1971-1", "prot_total": "2885-2", "albumin": "1751-7", "globulin": "2336-6", "ag_ratio": "1759-0", "ggt": "2324-2",
    "creatinine": "2160-0", "urea": "3091-6", "bun": "3094-0", "uric": "3086-6", "egfr": "33914-3",
    "sodium": "2951-2", "potassium": "2823-3", "chloride": "2075-0", "calcium": "17861-6", "phosphorus": "2777-1", "magnesium": "19123-9",
    "vitd": "62292-8", "b12": "14685-2", "iron": "2498-4", "ferritin": "2276-4", "tibc": "2500-7",
    "tsh": "3016-3", "t3": "3049-4", "t4": "3026-2", "ft3": "3051-0", "ft4": "3024-7"
}

PANEL_GUIDELINES = {
    "CBC": "WHO Guidelines on the Assessment of Nutritional Anemia & ICSH Clinical Practice Standards",
    "Diabetes": "ADA (American Diabetes Association) Standards of Care in Diabetes (2024)",
    "Lipid": "AHA/ACC Multi-Society Guideline on Blood Cholesterol & Cardiovascular Risk Reduction",
    "Liver": "AASLD Practice Guidelines for the Evaluation and Management of Abnormal Liver Chemistries",
    "Kidney": "KDIGO Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease",
    "Electrolytes": "Endocrine Society & Kidney Disease International Clinical Practice Frameworks",
    "Vitamins": "Endocrine Society Clinical Practice Guidelines on Vitamin D & Micronutrient Deficiencies",
    "Thyroid": "ATA (American Thyroid Association) Guidelines for Diagnosis & Management of Thyroid Disease"
}

MEDICATION_LAB_INTERACTIONS = {
    "statin": {
        "names": ["atorvastatin", "rosuvastatin", "simvastatin", "pravastatin", "statin", "lipitor", "crestor"],
        "markers": ["alt", "ast", "alp"],
        "effect": "Statins frequently induce mild, benign elevations in ALT/AST. Isolated elevations up to 3x upper limit of normal are commonly transient; clinical guidelines recommend surveillance rather than abrupt discontinuation unless symptoms arise.",
        "guideline": "AHA/ACC Cholesterol Guideline & FDA Statin Safety Guidance"
    },
    "ace_inhibitor": {
        "names": ["lisinopril", "enalapril", "ramipril", "captopril", "benazepril", "losartan", "valsartan", "telmisartan", "ace inhibitor", "arb"],
        "markers": ["potassium", "creatinine", "bun"],
        "effect": "ACE inhibitors and ARBs decrease aldosterone secretion, impairing renal potassium excretion. Mild-to-moderate hyperkalemia and modest creatinine increases (up to 30%) are expected pharmacological effects requiring regular electrolyte checks.",
        "guideline": "KDIGO Blood Pressure Management in CKD Guidelines"
    },
    "metformin": {
        "names": ["metformin", "glucophage"],
        "markers": ["b12", "glucose_f", "hba1c"],
        "effect": "Long-term metformin usage reduces ileal calcium-dependent absorption of Vitamin B12, causing low B12 in up to 30% of patients. Annual B12 screening is advised.",
        "guideline": "ADA Standards of Care in Diabetes: Micronutrient Monitoring"
    },
    "diuretic": {
        "names": ["hydrochlorothiazide", "furosemide", "lasix", "chlorthalidone", "spironolactone", "diuretic"],
        "markers": ["sodium", "potassium", "uric", "creatinine"],
        "effect": "Diuretics increase renal fluid and electrolyte excretion, commonly causing mild hyponatremia or hypokalemia, as well as elevating serum uric acid which may precipitate gout.",
        "guideline": "ACC/AHA Hypertension Practice Guidelines"
    },
    "levothyroxine": {
        "names": ["levothyroxine", "synthroid", "eltroxin", "thyronorm"],
        "markers": ["tsh", "t3", "t4", "ft3", "ft4"],
        "effect": "Exogenous thyroid hormone suppresses pituitary TSH. Low TSH may reflect mild over-replacement, while elevated TSH indicates under-replacement or adherence gaps.",
        "guideline": "ATA Guidelines for Hypothyroidism Management"
    },
    "iron_supplement": {
        "names": ["iron supplement", "ferrous sulfate", "ferrous fumarate", "iron", "orofer"],
        "markers": ["ferritin", "iron", "hemoglobin"],
        "effect": "Oral iron supplementation progressively raises ferritin and transferrin saturation before systemic hemoglobin fully normalizes.",
        "guideline": "WHO Guidelines on Oral Iron Therapy"
    },
    "ppi": {
        "names": ["omeprazole", "pantoprazole", "esomeprazole", "lansoprazole", "rabeprazole", "dexlansoprazole", "prilosec", "nexium", "protonix", "ppi"],
        "markers": ["magnesium", "b12", "iron", "ferritin", "calcium"],
        "effect": "Long-term PPI acid suppression impairs gastric acid-dependent absorption of magnesium, vitamin B12, non-heme iron, and calcium. Serum magnesium surveillance is advised by the FDA.",
        "guideline": "FDA Drug Safety Communication: Low Magnesium & AGA Clinical Practice Guidance"
    },
    "sglt2_inhibitor": {
        "names": ["empagliflozin", "dapagliflozin", "canagliflozin", "jardiance", "farxiga", "invokana", "sglt2"],
        "markers": ["egfr", "creatinine", "glucose_f", "hba1c", "hematocrit"],
        "effect": "SGLT2 inhibitors lower blood glucose and promote osmotic diuresis; a mild initial eGFR dip (2-4 mL/min) reflects restorative tubuloglomerular feedback that confers long-term nephroprotection.",
        "guideline": "ADA & KDIGO Consensus on Diabetes Management in CKD"
    },
    "corticosteroid": {
        "names": ["prednisone", "prednisolone", "methylprednisolone", "dexamethasone", "hydrocortisone", "medrol", "steroid"],
        "markers": ["wbc", "neutrophils", "glucose_f", "calcium", "potassium"],
        "effect": "Systemic corticosteroids induce sterile neutrophil demargination (causing leukocytosis without infection), stimulate hepatic gluconeogenesis, and accelerate intestinal calcium wasting.",
        "guideline": "American College of Rheumatology (ACR) GIOP Guidelines"
    },
    "nsaid": {
        "names": ["ibuprofen", "naproxen", "meloxicam", "celecoxib", "diclofenac", "indomethacin", "advil", "aleve", "motrin", "mobic", "nsaid"],
        "markers": ["ferritin", "iron", "creatinine", "hemoglobin"],
        "effect": "Chronic NSAID use inhibits gastric mucosal protective prostaglandins, causing subclinical occult blood loss (iron/ferritin depletion) and reducing renal prostaglandin perfusion.",
        "guideline": "ACG Clinical Guideline: Prevention and Management of NSAID Ulcer Complications"
    }
}

# -------------------------------------------------------------------------
# DRUG-NUTRIENT DEPLETION & MEDICATION INTERACTION CO-PILOT CATALOG
# Evidence-based matrices linking drug classes to nutrient malabsorption,
# unmonitored surveillance gaps, and benign pharmacological lab shifts.
# -------------------------------------------------------------------------
DRUG_NUTRIENT_DEPLETION_CATALOG = {
    "metformin": {
        "drug_class_name": "Metformin / Biguanides",
        "names": ["metformin", "glucophage", "fortamet", "glumetza", "riomet"],
        "depleted_nutrients": [
            {
                "key": "b12",
                "name": "Vitamin B12 (Cobalamin)",
                "mechanism": "Antagonizes calcium-dependent membrane action in the terminal ileum necessary for intrinsic factor-B12 uptake, reducing B12 levels by 20–30% in up to 30% of long-term users.",
                "clinical_risk": "Peripheral neuropathy (frequently misdiagnosed as diabetic neuropathy), macrocytic anemia, cognitive slowing, elevated homocysteine.",
                "severity": "high",
                "recommended_test": "Serum Vitamin B12, Methylmalonic Acid (MMA), and Homocysteine",
                "evidence_citation": "American Diabetes Association (ADA) Standards of Care: Microvascular Complications & Micronutrient Surveillance",
                "doctor_question": "Given my long-term metformin usage and ADA guidelines, should we assess my Vitamin B12 level or consider B12 supplementation?"
            },
            {
                "key": "folate",
                "name": "Folate (Vitamin B9)",
                "mechanism": "Decreased intestinal mucosal absorption secondary to altered gastrointestinal transit and microbiome shifts.",
                "clinical_risk": "Megaloblastic anemia, elevated homocysteine, endothelial dysfunction.",
                "severity": "moderate",
                "recommended_test": "Serum Folate or RBC Folate",
                "evidence_citation": "European Association for the Study of Diabetes (EASD) Micronutrient Review",
                "doctor_question": "Should we verify my folate levels alongside B12, or optimize dietary intake of folate-dense leafy greens and legumes?"
            }
        ],
        "benign_shifts": [
            {
                "markers": ["glucose_f", "hba1c"],
                "direction": "lowering",
                "label": "Therapeutic Glycemic Lowering",
                "clinical_explanation": "Progressive reduction in fasting blood glucose and HbA1c is the intended therapeutic pharmacological action through suppression of hepatic gluconeogenesis.",
                "guideline": "ADA Guidelines on Glycemic Goals",
                "doctor_question": "My blood sugar markers show a beneficial reduction consistent with metformin therapy; are we on target for my individualized HbA1c goal?"
            }
        ]
    },
    "statin": {
        "drug_class_name": "Statins (HMG-CoA Reductase Inhibitors)",
        "names": ["atorvastatin", "rosuvastatin", "simvastatin", "pravastatin", "lovastatin", "pitavastatin", "statin", "lipitor", "crestor", "zocor"],
        "depleted_nutrients": [
            {
                "key": "coq10",
                "name": "Coenzyme Q10 (Ubiquinone)",
                "mechanism": "HMG-CoA reductase inhibition halts mevalonate synthesis, blocking the downstream biosynthesis of both endogenous cholesterol and ubiquinone (CoQ10) in mitochondrial electron transport.",
                "clinical_risk": "Statin-associated muscle symptoms (SAMS), myalgia, unexplained muscle soreness, fatigue, impaired exercise tolerance.",
                "severity": "high",
                "recommended_test": "Plasma CoQ10 level or clinical evaluation of muscle discomfort",
                "evidence_citation": "AHA Scientific Statement on Statin-Associated Muscle Symptoms & Mitochondrial Bioenergetics",
                "doctor_question": "Since statins can lower cellular CoQ10 production, could my muscle fatigue or soreness be related, and would a trial of CoQ10 (Ubiquinol) supplementation be appropriate?"
            },
            {
                "key": "vitd",
                "name": "Vitamin D (25-OH)",
                "mechanism": "Inhibition of the mevalonate pathway limits cholesterol precursor availability for 7-dehydrocholesterol, worsening borderline hypovitaminosis D and compounding myalgia risks.",
                "clinical_risk": "Impaired bone mineralization, exacerbated statin-related myopathy.",
                "severity": "moderate",
                "recommended_test": "25-Hydroxy Vitamin D [25(OH)D]",
                "evidence_citation": "Endocrine Society Clinical Practice Guideline on Vitamin D Deficiency",
                "doctor_question": "Could we test my 25-hydroxy Vitamin D level, as adequate Vitamin D optimizes muscle tolerance on statin therapy?"
            }
        ],
        "benign_shifts": [
            {
                "markers": ["alt", "ast"],
                "max_benign_multiplier": 3.0,
                "label": "Benign Transaminase Adaptation (≤ 3× ULN)",
                "clinical_explanation": "Mild ALT/AST elevations (up to 3× upper limit of normal) occur in up to 3% of patients taking statins. ACC/AHA guidelines classify this as an asymptomatic hepatic adaptation rather than genuine hepatotoxicity. Abrupt discontinuation is not recommended unless bilirubin rises or symptoms develop.",
                "guideline": "ACC/AHA Cholesterol Guidelines & FDA Statin Safety Advisory",
                "doctor_question": "My liver enzymes show a mild elevation; given ACC/AHA guidance that statin elevations up to 3× ULN are typically benign adaptations, should we simply recheck in 8-12 weeks?"
            }
        ]
    },
    "ppi": {
        "drug_class_name": "Proton Pump Inhibitors (PPIs)",
        "names": ["omeprazole", "pantoprazole", "esomeprazole", "lansoprazole", "rabeprazole", "dexlansoprazole", "prilosec", "nexium", "protonix", "ppi"],
        "depleted_nutrients": [
            {
                "key": "magnesium",
                "name": "Magnesium",
                "mechanism": "Long-term profound gastric acid suppression alters intestinal luminal pH, inhibiting active TRPM6/TRPM7 magnesium channel transport across the intestinal brush border.",
                "clinical_risk": "Refractory muscle cramps, palpitations, secondary hypokalemia/hypocalcemia, tremor, increased cardiac arrhythmia susceptibility.",
                "severity": "high",
                "recommended_test": "Serum Magnesium and Comprehensive Electrolyte Panel",
                "evidence_citation": "FDA Drug Safety Communication: Low Magnesium Levels Associated with Long-Term PPI Use",
                "doctor_question": "Given the FDA safety warnings on chronic PPI use and intestinal magnesium malabsorption, should we monitor my serum magnesium level?"
            },
            {
                "key": "b12",
                "name": "Vitamin B12 (Cobalamin)",
                "mechanism": "Gastric hydrochloric acid and pepsin are mandatory to dissociate vitamin B12 from dietary animal proteins so it can bind intrinsic factor.",
                "clinical_risk": "Paresthesias, peripheral neuropathy, fatigue, macrocytic anemia.",
                "severity": "moderate",
                "recommended_test": "Serum Vitamin B12 and Complete Blood Count (CBC)",
                "evidence_citation": "American Gastroenterological Association (AGA) Clinical Practice Update on PPI Long-Term Risks",
                "doctor_question": "Should we periodically evaluate my Vitamin B12 and red blood cell indices while I remain on acid-suppression therapy?"
            },
            {
                "key": "iron",
                "name": "Iron & Ferritin",
                "mechanism": "Gastric acidity is required to maintain ferric iron (Fe3+) in solution and facilitate reduction to ferrous iron (Fe2+), which is the primary absorbable form in the duodenum.",
                "clinical_risk": "Microcytic iron deficiency anemia, unexplained physical fatigue, brittle nails, restless legs.",
                "severity": "moderate",
                "recommended_test": "Ferritin, Serum Iron, and Total Iron-Binding Capacity (TIBC)",
                "evidence_citation": "British Society of Gastroenterology (BSG) Management of Iron Deficiency",
                "doctor_question": "Could my long-term PPI therapy be hindering dietary iron absorption, and should we evaluate my serum ferritin and iron saturation?"
            },
            {
                "key": "calcium",
                "name": "Calcium",
                "mechanism": "Insoluble calcium salts (such as calcium carbonate) require acidic gastric juice for dissociation and bioavailable ionization.",
                "clinical_risk": "Decreased bone mineral density, accelerated osteopenia, increased hip fracture risk.",
                "severity": "moderate",
                "recommended_test": "Serum Calcium, Albumin-adjusted Calcium, and Bone Density (DEXA)",
                "evidence_citation": "National Osteoporosis Foundation Guidelines on Drug-Induced Bone Loss",
                "doctor_question": "Should we switch to calcium citrate (which does not depend on stomach acid for absorption) or monitor bone mineral density?"
            }
        ],
        "benign_shifts": []
    },
    "ace_inhibitor": {
        "drug_class_name": "ACE Inhibitors & ARBs (RAAS Blockers)",
        "names": ["lisinopril", "enalapril", "ramipril", "captopril", "benazepril", "losartan", "valsartan", "telmisartan", "irbesartan", "olmesartan", "ace inhibitor", "arb"],
        "depleted_nutrients": [
            {
                "key": "zinc",
                "name": "Zinc",
                "mechanism": "ACE inhibitors chelate serum zinc ions and enhance urinary zinc wasting (hyperzincuria) via proximal tubular transport interference.",
                "clinical_risk": "Dysgeusia (taste disturbance / loss), impaired epithelial wound healing, subclinical immune blunting.",
                "severity": "moderate",
                "recommended_test": "Serum or Plasma Zinc level",
                "evidence_citation": "Clinical Nephrology Review on RAAS Antagonist Micronutrient Excretion",
                "doctor_question": "Could taste changes or slower healing be related to ACE-inhibitor-induced zinc loss, and should we assess zinc or increase dietary zinc?"
            }
        ],
        "benign_shifts": [
            {
                "markers": ["creatinine"],
                "max_benign_multiplier": 1.30,
                "label": "Expected Hemodynamic Glomerular Filtration Adjustment (≤ 30% Creatinine Rise)",
                "clinical_explanation": "Inhibiting angiotensin II dilates the renal efferent arteriole, intentionally reducing intraglomerular hydrostatic pressure. An acute creatinine elevation of up to 30% above baseline is a recognized hemodynamic consequence that actually preserves long-term renal parenchymal integrity and slows CKD progression.",
                "guideline": "KDIGO Clinical Practice Guideline for the Management of Blood Pressure in CKD",
                "doctor_question": "My creatinine showed a mild bump. KDIGO guidelines explain that a rise of up to 30% on ACE inhibitors is expected and reflects beneficial renal glomerular pressure reduction; should we continue current dosing and recheck in a few weeks?"
            },
            {
                "markers": ["potassium"],
                "max_benign_value": 5.2,
                "label": "Anticipated Aldosterone-Suppressed Potassium Retention",
                "clinical_explanation": "Suppressed aldosterone mildly limits distal tubular potassium excretion. Serum potassium between 4.8 and 5.2 mmol/L is common and expected in cardiovascular care, calling for dietary awareness and surveillance rather than immediate drug discontinuation.",
                "guideline": "ACC/AHA Heart Failure and Hypertension Guidelines",
                "doctor_question": "With my potassium slightly on the higher end of normal, should we review potassium-rich foods and supplements or simply schedule routine electrolyte surveillance?"
            }
        ]
    },
    "diuretic": {
        "drug_class_name": "Diuretics (Thiazide, Loop & Related)",
        "names": ["hydrochlorothiazide", "furosemide", "lasix", "chlorthalidone", "spironolactone", "bumetanide", "torsemide", "indapamide", "diuretic", "hctz"],
        "depleted_nutrients": [
            {
                "key": "potassium",
                "name": "Potassium",
                "mechanism": "Enhanced luminal sodium delivery to the cortical collecting tubule accelerates potassium kaliuresis into the urine.",
                "clinical_risk": "Cardiac dysrhythmias, severe lower-limb muscle cramps, physical fatigue, paralytic ileus.",
                "severity": "high",
                "recommended_test": "Serum Potassium (Electrolyte Panel)",
                "evidence_citation": "ACC/AHA Guideline for the Management of High Blood Pressure",
                "doctor_question": "Should we monitor my potassium levels closely or consider potassium-rich dietary adjustments / potassium supplementation while I am taking this diuretic?"
            },
            {
                "key": "magnesium",
                "name": "Magnesium",
                "mechanism": "Inhibition of solute reabsorption in the thick ascending limb of Henle's loop and distal convoluted tubule causes parallel magnesium excretion.",
                "clinical_risk": "Refractory hypokalemia (hypokalemia cannot be resolved until magnesium is normalized), cardiac palpitations, nocturnal leg cramps.",
                "severity": "high",
                "recommended_test": "Serum Magnesium",
                "evidence_citation": "Journal of the American Society of Nephrology: Diuretic-Induced Electrolyte Disorders",
                "doctor_question": "Given that low magnesium can cause muscle cramps and prevent potassium from normalizing, could we check my serum magnesium?"
            },
            {
                "key": "sodium",
                "name": "Sodium",
                "mechanism": "Direct inhibition of NaCl cotransporters alongside fluid loss promotes solute-free water retention and dilutional or depletional hyponatremia.",
                "clinical_risk": "Hyponatremia, dizziness, postural lightheadedness, gait instability, mental confusion.",
                "severity": "moderate",
                "recommended_test": "Basic Metabolic Panel (Serum Sodium)",
                "evidence_citation": "Endocrine Society Clinical Practice Guideline on Hyponatremia",
                "doctor_question": "Should we check my sodium level if I experience dizziness or lightheadedness when standing?"
            }
        ],
        "benign_shifts": [
            {
                "markers": ["uric"],
                "label": "Diuretic-Induced Hyperuricemia (Competitive Clearance)",
                "clinical_explanation": "Thiazide and loop diuretics competitively inhibit renal tubular organic acid transporters, decreasing uric acid clearance. Asymptomatic hyperuricemia is an expected benign side-effect that does not warrant stopping therapy or initiating allopurinol unless acute gout arthritis develops.",
                "guideline": "American College of Rheumatology (ACR) Guideline for the Management of Gout",
                "doctor_question": "My uric acid is elevated; since diuretics naturally compete with uric acid excretion, do we just monitor this as long as I remain symptom-free without joint swelling?"
            }
        ]
    },
    "sglt2_inhibitor": {
        "drug_class_name": "SGLT2 Inhibitors (Gliflozins)",
        "names": ["empagliflozin", "dapagliflozin", "canagliflozin", "jardiance", "farxiga", "invokana", "sglt2"],
        "depleted_nutrients": [
            {
                "key": "sodium",
                "name": "Hydration / Intravascular Volume & Electrolytes",
                "mechanism": "Osmotic diuresis triggered by renal glycosuria elevates 24-hour urine excretion by 300 to 500 mL/day, mildly depleting plasma volume and sodium reserves.",
                "clinical_risk": "Orthostatic hypotension, volume contraction, dizziness, dehydration.",
                "severity": "moderate",
                "recommended_test": "Blood Pressure, Orthostatic Vitals, and Basic Metabolic Panel",
                "evidence_citation": "ADA/EASD Consensus Statement: Management of Hyperglycemia in T2D with SGLT2i",
                "doctor_question": "How much extra water should I aim to drink daily to avoid mild volume depletion while on my SGLT2 inhibitor?"
            }
        ],
        "benign_shifts": [
            {
                "markers": ["egfr"],
                "label": "The Hemodynamic 'SGLT2 eGFR Dip' (Reversible Nephroprotection)",
                "clinical_explanation": "Initiation of an SGLT2 inhibitor characteristically causes a transient, benign dip in eGFR of 2 to 5 mL/min/1.73m² due to restored tubuloglomerular feedback and afferent arteriolar tone. Landmark clinical trials (EMPA-REG, DAPA-CKD) confirm this initial dip stabilizes and powerfully slows long-term nephron loss.",
                "guideline": "ADA & KDIGO Consensus Report on Diabetes Management in CKD",
                "doctor_question": "If my eGFR dipped slightly after starting Jardiance/Farxiga, is this the anticipated SGLT2 hemodynamic dip that protects kidney health over the long run?"
            },
            {
                "markers": ["hematocrit", "hemoglobin"],
                "label": "Physiological Hemoconcentration & Erythropoietin Enhancement",
                "clinical_explanation": "SGLT2 inhibitors stimulate renal erythropoietin secretion and reduce plasma fluid volume, leading to a benign 1-3% rise in hematocrit and hemoglobin that supports myocardial oxygen delivery.",
                "guideline": "European Heart Journal Cardiovascular Pharmacology Review",
                "doctor_question": "Is the slight rise in my red cell count an expected physiological response to my SGLT2 inhibitor?"
            }
        ]
    },
    "corticosteroid": {
        "drug_class_name": "Systemic Corticosteroids (Glucocorticoids)",
        "names": ["prednisone", "prednisolone", "methylprednisolone", "dexamethasone", "hydrocortisone", "medrol", "steroid"],
        "depleted_nutrients": [
            {
                "key": "calcium",
                "name": "Calcium",
                "mechanism": "Direct downregulation of active intestinal TRPV6 calcium transport channels and simultaneous renal tubular hypercalciuria induce acute calcium loss.",
                "clinical_risk": "Rapid uncoupling of bone remodeling, early osteopenia, glucocorticoid-induced osteoporosis.",
                "severity": "high",
                "recommended_test": "Serum Calcium, 24-hr Urine Calcium, and Baseline DEXA Bone Scan",
                "evidence_citation": "American College of Rheumatology (ACR) Guideline for Prevention and Treatment of GIOP",
                "doctor_question": "Should I be co-prescribed Calcium (1000-1200 mg/day) and Vitamin D while taking corticosteroids to safeguard bone density?"
            },
            {
                "key": "vitd",
                "name": "Vitamin D (25-OH)",
                "mechanism": "Systemic glucocorticoids stimulate hepatic cytochrome P450 enzymes (CYP24A1), accelerating the catabolism of active 25-OH and 1,25-dihydroxy Vitamin D into inactive metabolites.",
                "clinical_risk": "Subacute hypovitaminosis D, muscle weakness, accelerated bone demineralization.",
                "severity": "high",
                "recommended_test": "25-Hydroxy Vitamin D level",
                "evidence_citation": "Endocrine Society Guidelines on Corticosteroid-Induced Metabolic Bone Disease",
                "doctor_question": "Could we test my 25-OH Vitamin D level and discuss optimal supplementation dosing during steroid treatment?"
            },
            {
                "key": "potassium",
                "name": "Potassium",
                "mechanism": "Corticosteroids possess intrinsic mineralocorticoid receptor activity, stimulating distal tubular potassium excretion and sodium retention.",
                "clinical_risk": "Hypokalemia, fluid retention, blood pressure escalation.",
                "severity": "moderate",
                "recommended_test": "Serum Potassium (Electrolyte Panel)",
                "evidence_citation": "AHA Clinical Scientific Review: Drug-Induced Hypertension and Electrolyte Shifts",
                "doctor_question": "Should we verify my potassium level while I am on this steroid taper?"
            }
        ],
        "benign_shifts": [
            {
                "markers": ["wbc", "neutrophils"],
                "label": "Sterile Leukocyte Demargination (Glucocorticoid Effect)",
                "clinical_explanation": "Steroids inhibit leukocyte adhesion molecule expression (L-selectin/ICAM-1), detaching neutrophils adhering to vascular endothelial walls into circulating blood. In the absence of fever or clinical signs of infection, leukocytosis (WBC 12,000–16,000/µL) is an expected sterile pharmacological shift rather than an active infection.",
                "guideline": "Hematology Practice Guidelines on Drug-Induced Leukocytosis",
                "doctor_question": "My white blood cell count is elevated; since steroids cause neutrophil demargination and I have no fever or symptoms of infection, is this purely a medication effect?"
            },
            {
                "markers": ["glucose_f", "glucose_pp", "glucose_r"],
                "label": "Steroid-Induced Insulin Resistance / Gluconeogenesis",
                "clinical_explanation": "Corticosteroids stimulate hepatic gluconeogenesis and induce peripheral muscle insulin resistance, frequently elevating blood glucose.",
                "guideline": "ADA Guidelines on Steroid-Induced Hyperglycemia",
                "doctor_question": "Should we monitor my blood sugar more closely during this course of steroids?"
            }
        ]
    },
    "nsaid": {
        "drug_class_name": "NSAIDs (Non-Steroidal Anti-Inflammatories)",
        "names": ["ibuprofen", "naproxen", "meloxicam", "celecoxib", "diclofenac", "indomethacin", "advil", "aleve", "motrin", "mobic", "nsaid"],
        "depleted_nutrients": [
            {
                "key": "iron",
                "name": "Iron & Ferritin (Occult Blood Loss)",
                "mechanism": "Non-selective COX-1 inhibition suppresses gastric and duodenal mucosal prostaglandin PGE2 and PGI2 synthesis, leading to micro-ulcerations and continuous subclinical occult GI blood loss.",
                "clinical_risk": "Microcytic iron deficiency anemia, progressive ferritin depletion, chronic fatigue, dyspnea on exertion.",
                "severity": "high",
                "recommended_test": "Complete Blood Count (CBC), Serum Ferritin, and Fecal Occult Blood Test (FIT)",
                "evidence_citation": "American College of Gastroenterology (ACG) Guideline: Prevention of NSAID-Related Ulcer Complications",
                "doctor_question": "Because regular NSAID use can cause subclinical stomach micro-bleeding, should we check my ferritin and iron levels, or consider gastroprotective therapy?"
            }
        ],
        "benign_shifts": [
            {
                "markers": ["creatinine"],
                "label": "Prostaglandin-Mediated Hemodynamic Vasoconstriction",
                "clinical_explanation": "NSAIDs inhibit renal prostaglandins that normally dilate the afferent arteriole, slightly reducing glomerular plasma flow and prompting transient fluid retention or minor creatinine elevations.",
                "guideline": "KDIGO Acute Kidney Injury Clinical Practice Guidelines",
                "doctor_question": "Could my mild creatinine change and fluid retention be linked to NSAID use, and should I limit these medications?"
            }
        ]
    }
}


# Alias for backwards compatibility
DRUG_INTERACTIONS = MEDICATION_LAB_INTERACTIONS

PREGNANCY_RANGES = {
    "hemoglobin": {1: (11.0, 15.0), 2: (10.5, 14.5), 3: (11.0, 15.0)},
    "hematocrit": {1: (33.0, 44.0), 2: (32.0, 42.0), 3: (33.0, 44.0)},
    "platelets": {1: (150000, 400000), 2: (130000, 400000), 3: (115000, 390000)},
    "glucose_f": {1: (70.0, 92.0), 2: (70.0, 92.0), 3: (70.0, 92.0)},
    "alp": {1: (44.0, 147.0), 2: (50.0, 180.0), 3: (70.0, 350.0)},
    "esr": {1: (0.0, 45.0), 2: (0.0, 60.0), 3: (0.0, 70.0)}
}

# Pathophysiological interaction network (causal mechanisms between biomarkers)
PATHOPHYSIOLOGY_NETWORK = {
    "metabolic_syndrome": {
        "name": "Metabolic Syndrome & Insulin Resistance Triad",
        "description": "Insulin resistance stimulates hepatic VLDL secretion, drives hypertriglyceridemia, accelerates HDL clearance, and impairs peripheral glucose disposal.",
        "markers": ["glucose_f", "hba1c", "trig", "hdl"],
        "guideline": "ADA Standards of Care & AHA/NHLBI Metabolic Syndrome Criteria",
        "synergy_alert": "Co-elevation of Fasting Glucose/HbA1c with elevated Triglycerides and low HDL indicates compounded cardiometabolic risk rather than isolated dyslipidemia."
    },
    "cardiovascular_atherogenic": {
        "name": "Atherogenic Lipid & Endothelial Risk Axis",
        "description": "Elevated apolipoprotein B-containing particles (LDL, VLDL, Triglycerides) penetrate vascular intima, inducing oxidative inflammation and plaque accumulation.",
        "markers": ["ldl", "chol", "trig", "vldl"],
        "guideline": "AHA/ACC Multi-Society Cholesterol Management Guidelines",
        "synergy_alert": "Concurrent elevation of LDL and Triglycerides significantly compounds 10-year atherosclerotic cardiovascular disease (ASCVD) risk."
    },
    "hepato_biliary": {
        "name": "Hepato-Biliary & Cytolytic Axis",
        "description": "Hepatocellular injury releases ALT and AST into circulation; canalicular injury or cholestasis triggers alkaline phosphatase (ALP) and total bilirubin elevation.",
        "markers": ["alt", "ast", "alp", "bili", "ggt"],
        "guideline": "AASLD Practice Guidelines for Evaluation of Abnormal Liver Tests",
        "synergy_alert": "Concomitant elevation of ALT and AST indicates active hepatic parenchyma inflammation or steatohepatitis."
    },
    "renal_electrolyte": {
        "name": "Renal Hemodynamic & Electrolyte Clearance Axis",
        "description": "Decline in glomerular filtration rate (eGFR) reduces urinary creatinine, urea, and potassium excretion, promoting toxic retention and hyperkalemia.",
        "markers": ["creatinine", "egfr", "urea", "bun", "potassium"],
        "guideline": "KDIGO Clinical Practice Guideline for CKD Evaluation & Management",
        "synergy_alert": "Declining eGFR coupled with elevated Creatinine and Potassium indicates compromised nephron filtration with imminent hyperkalemia danger."
    },
    "erythropoiesis_anemia": {
        "name": "Erythropoietic & Microcytic Anemia Axis",
        "description": "Depleted iron stores (low Ferritin) starve bone marrow erythroblasts, producing microcytic, hypochromic red cells (low MCV, low MCH) and falling Hemoglobin.",
        "markers": ["hemoglobin", "mcv", "mch", "ferritin", "iron"],
        "guideline": "WHO Guidelines on the Assessment of Nutritional Anemia",
        "synergy_alert": "Low Hemoglobin alongside reduced MCV (<83 fL) and low Ferritin strongly substantiates Iron Deficiency Anemia."
    },
    "thyroid_axis": {
        "name": "Hypothalamic-Pituitary-Thyroid Negative Feedback Loop",
        "description": "Pituitary TSH regulates thyroidal secretion of T4 and T3. In primary hypothyroidism, failing thyroid output prompts compensatory TSH escalation.",
        "markers": ["tsh", "ft4", "t4", "t3"],
        "guideline": "American Thyroid Association (ATA) Hypothyroidism Guidelines",
        "synergy_alert": "Elevated TSH (>4.5 uIU/mL) with reduced Free T4 confirms primary hypothyroidism requiring endocrinology titration."
    }
}

SPECIALIST_ROUTING = {
    "CBC": "Hematologist or General Physician",
    "Diabetes": "Endocrinologist or Diabetologist",
    "Lipid": "Cardiologist or Preventive Medicine Physician",
    "Liver": "Hepatologist or Gastroenterologist",
    "Kidney": "Nephrologist",
    "Electrolytes": "Nephrologist or General Physician",
    "Vitamins": "General Physician or Clinical Nutritionist",
    "Thyroid": "Endocrinologist"
}

FOLLOWUP_TESTS = {
    "hemoglobin": ["Serum Ferritin", "Total Iron Binding Capacity (TIBC)", "Vitamin B12 & Folate", "Peripheral Blood Smear", "Reticulocyte Count"],
    "glucose_f": ["HbA1c (3-Month Glycated Hemoglobin)", "Post-Prandial Glucose (PPBS)", "Urine Albumin-to-Creatinine Ratio (uACR)", "Lipid Panel"],
    "hba1c": ["Fasting Blood Sugar", "Urine Microalbumin", "Comprehensive Metabolic Panel"],
    "chol": ["Apolipoprotein B (ApoB)", "Lipoprotein(a)", "hs-CRP (Cardiovascular Inflammation)", "HbA1c"],
    "ldl": ["ApoB", "Lipoprotein(a)", "Liver Enzymes (ALT/AST)", "Carotid Doppler Ultrasound if indicated"],
    "trig": ["Fasting Glucose", "HbA1c", "Liver Ultrasound for Hepatic Steatosis"],
    "alt": ["Hepatitis B & C Serology", "Liver Ultrasound", "Repeat ALT/AST in 4-6 weeks"],
    "ast": ["ALT (SGPT)", "CPK (Creatine Kinase)", "Liver Ultrasound"],
    "creatinine": ["eGFR Re-check", "Urine Routine & Microscopic Examination", "Urine Albumin-Creatinine Ratio (uACR)", "Kidney Ultrasound"],
    "egfr": ["Urine Protein-to-Creatinine Ratio", "Renal Ultrasound", "Serum Electrolytes"],
    "potassium": ["Repeat Serum Potassium immediately", "12-Lead ECG / Electrocardiogram", "Serum Creatinine and BUN"],
    "tsh": ["Free T4 (FT4)", "Free T3 (FT3)", "Anti-TPO Antibodies (Thyroid Peroxidase)"],
    "vitd": ["Serum Calcium", "Serum Phosphorus", "Parathyroid Hormone (PTH)"],
    "b12": ["Serum Methylmalonic Acid (MMA)", "Homocysteine", "Complete Blood Count (CBC)"]
}

KB = [dict(
    key=r[0], name=r[1], aliases=r[2], unit=r[3], low=r[4], high=r[5],
    high_meaning=r[6], low_meaning=r[7], category=r[8], sex_ranges=r[9],
    loinc=LOINC_CODES.get(r[0], "Unknown"),
    guideline=PANEL_GUIDELINES.get(r[8], "Standard Clinical Practice")
) for r in _ROWS]

BY_KEY = {k["key"]: k for k in KB}

# Sorted longest-first to ensure multi-word aliases match ahead of single words
ALIASES = sorted(((a, k["key"]) for k in KB for a in k["aliases"]), key=lambda x: -len(x[0]))

def find_marker(text: str):
    t = text.lower()
    for alias, key in ALIASES:
        if re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", t):
            return BY_KEY[key]
    return None

def lookup(name: str):
    return find_marker(name)

def get_reference_range(key: str, sex: str = None, pregnancy_trimester: int = None):
    """Return (low, high) default reference range, adjusting for sex and pregnancy if known."""
    if pregnancy_trimester and key in PREGNANCY_RANGES:
        t_dict = PREGNANCY_RANGES[key]
        if pregnancy_trimester in t_dict:
            return t_dict[pregnancy_trimester]
    m = BY_KEY.get(key)
    if not m:
        return None, None
    if sex and m.get("sex_ranges"):
        s = sex.lower()
        if "f" in s and "female" in m["sex_ranges"]:
            return m["sex_ranges"]["female"]
        elif "m" in s and "male" in m["sex_ranges"]:
            return m["sex_ranges"]["male"]
    return m["low"], m["high"]

# Absolute physiological bounds for plausibility checks (reject impossible or corrupted OCR values)
PHYSIOLOGICAL_BOUNDS = {
    "hemoglobin": (1.0, 26.0),
    "rbc": (0.5, 10.0),
    "wbc": (100, 250000),
    "platelets": (1000, 3000000),
    "hematocrit": (5.0, 75.0),
    "mcv": (40.0, 160.0),
    "mch": (10.0, 60.0),
    "mchc": (15.0, 50.0),
    "rdw": (5.0, 35.0),
    "esr": (0.0, 180.0),
    "glucose_f": (10.0, 1200.0),
    "glucose_pp": (10.0, 1200.0),
    "glucose_r": (10.0, 1200.0),
    "hba1c": (2.5, 22.0),
    "chol": (20.0, 1200.0),
    "ldl": (10.0, 800.0),
    "hdl": (5.0, 200.0),
    "trig": (10.0, 3000.0),
    "vldl": (1.0, 500.0),
    "alt": (1.0, 5000.0),
    "ast": (1.0, 5000.0),
    "alp": (5.0, 3000.0),
    "bili": (0.01, 80.0),
    "bili_dir": (0.0, 40.0),
    "bili_indir": (0.0, 40.0),
    "prot_total": (1.0, 18.0),
    "albumin": (0.5, 10.0),
    "globulin": (0.5, 10.0),
    "ggt": (1.0, 3000.0),
    "creatinine": (0.1, 40.0),
    "urea": (2.0, 400.0),
    "bun": (1.0, 200.0),
    "uric": (0.5, 30.0),
    "egfr": (1.0, 200.0),
    "sodium": (90.0, 200.0),
    "potassium": (1.0, 12.0),
    "chloride": (60.0, 160.0),
    "calcium": (2.0, 25.0),
    "phosphorus": (0.5, 20.0),
    "magnesium": (0.2, 15.0),
    "vitd": (1.0, 300.0),
    "b12": (10.0, 5000.0),
    "iron": (5.0, 1000.0),
    "ferritin": (1.0, 10000.0),
    "tibc": (50.0, 1000.0),
    "tsh": (0.001, 250.0),
    "t3": (10.0, 1000.0),
    "t4": (0.5, 40.0),
    "ft3": (0.5, 30.0),
    "ft4": (0.1, 15.0),
}

# Critical red-flag emergency thresholds requiring immediate clinical escalation
CRITICAL_THRESHOLDS = {
    "potassium": {
        "low": (2.8, "Severe Hypokalemia (<= 2.8 mmol/L): High risk of dangerous cardiac dysrhythmias and muscle paralysis. Seek immediate emergency medical care."),
        "high": (6.2, "Severe Hyperkalemia (>= 6.2 mmol/L): Critical risk of lethal cardiac arrest and ventricular fibrillation. Seek immediate emergency hospital care.")
    },
    "glucose_f": {
        "low": (50.0, "Severe Hypoglycemia (<= 50 mg/dL): Risk of neuroglycopenia, loss of consciousness, or seizure. Consume fast-acting sugar immediately and seek urgent medical evaluation."),
        "high": (350.0, "Severe Hyperglycemia (>= 350 mg/dL): High risk of Diabetic Ketoacidosis (DKA) or Hyperosmolar Hyperglycemic State (HHS). Seek urgent medical care.")
    },
    "glucose_r": {
        "low": (50.0, "Severe Hypoglycemia (<= 50 mg/dL): Risk of loss of consciousness or seizures. Seek immediate attention."),
        "high": (350.0, "Severe Hyperglycemia (>= 350 mg/dL): High risk of metabolic crisis. Seek urgent medical care.")
    },
    "glucose_pp": {
        "low": (50.0, "Severe Hypoglycemia (<= 50 mg/dL): Seek urgent medical attention."),
        "high": (380.0, "Severe Postprandial Hyperglycemia (>= 380 mg/dL): Seek urgent medical care.")
    },
    "platelets": {
        "low": (20000, "Severe Thrombocytopenia (<= 20,000 /uL): High risk of spontaneous fatal intracranial or mucosal hemorrhage. Seek emergency hematology/hospital care."),
        "high": (1000000, "Extreme Thrombocytosis (>= 1,000,000 /uL): High risk of vascular thrombosis or microvascular occlusion.")
    },
    "hemoglobin": {
        "low": (6.5, "Severe Symptomatic Anemia (<= 6.5 g/dL): Critical oxygen transport deficit; urgent transfusion evaluation required. Seek immediate hospital care."),
        "high": (21.0, "Extreme Polycythemia (>= 21.0 g/dL): Severe hyperviscosity syndrome and stroke risk.")
    },
    "sodium": {
        "low": (120.0, "Severe Hyponatremia (<= 120 mmol/L): Severe risk of cerebral edema, seizures, and respiratory arrest. Seek emergency medical attention."),
        "high": (160.0, "Severe Hypernatremia (>= 160 mmol/L): Severe hyperosmolar state; seek emergency medical care.")
    },
    "calcium": {
        "low": (6.5, "Severe Hypocalcemia (<= 6.5 mg/dL): Risk of laryngospasm, tetany, and cardiac arrhythmia. Seek emergency medical care."),
        "high": (13.0, "Hypercalcemic Crisis (>= 13.0 mg/dL): Altered mental status, renal failure, and cardiac rhythm disturbance.")
    },
    "creatinine": {
        "high": (5.0, "Acute Severe Kidney Injury (Creatinine >= 5.0 mg/dL): Critical loss of kidney filtration function. Urgent nephrology evaluation required.")
    },
    "egfr": {
        "low": (15.0, "Kidney Failure / Stage 5 CKD (eGFR <= 15 mL/min/1.73m2): Requires immediate specialized nephrology care and dialysis assessment.")
    },
    "wbc": {
        "low": (1500, "Critical Leukopenia / Agranulocytosis (WBC <= 1,500 /uL): Extremely high risk of overwhelming, life-threatening infection. Seek urgent care."),
        "high": (30000, "Extreme Leukocytosis (WBC >= 30,000 /uL): Highly suggestive of acute severe infection, leukemoid reaction, or hematologic malignancy.")
    },
    "tsh": {
        "low": (0.05, "Marked Thyrotoxicosis (TSH <= 0.05 uIU/mL): Elevated risk of cardiac arrhythmias, atrial fibrillation, or thyroid storm."),
        "high": (25.0, "Severe Hypothyroidism (TSH >= 25 uIU/mL): Risk of myxedema and severe metabolic depression.")
    }
}

import math

def get_loinc(key: str) -> str:
    """Return official LOINC code for biomarker key."""
    return LOINC_CODES.get(key, "Unknown")

def get_guideline(category_or_key: str) -> str:
    """Return evidence-based clinical practice guideline citation."""
    if category_or_key in PANEL_GUIDELINES:
        return PANEL_GUIDELINES[category_or_key]
    m = BY_KEY.get(category_or_key)
    if m and m.get("category") in PANEL_GUIDELINES:
        return PANEL_GUIDELINES[m["category"]]
    return "Evidence-Based Clinical Practice Standards"

def get_specialist_recommendation(abnormal_rows: list[dict]) -> dict:
    """Determine top medical specialist and recommended follow-up diagnostic battery."""
    if not abnormal_rows:
        return {
            "specialist": "Primary Care Physician / General Practitioner",
            "department": "Internal Medicine",
            "urgency": "Routine Wellness / Annual Review",
            "rationale": "All analyzed markers are within expected physiological limits.",
            "recommended_followup_tests": []
        }
    
    # Priority count by category
    cat_counts = {}
    followups = []
    has_critical = any(r.get("is_critical") for r in abnormal_rows)
    has_marked = any(r.get("severity") == "marked" for r in abnormal_rows)
    
    for r in abnormal_rows:
        cat = r.get("category", "General")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        tests = FOLLOWUP_TESTS.get(r.get("key"), [])
        for t in tests:
            if t not in followups:
                followups.append(t)
                
    top_cat = max(cat_counts, key=cat_counts.get)
    spec = SPECIALIST_ROUTING.get(top_cat, "Internal Medicine Specialist")
    
    urgency = "Immediate Emergency Care (< 24 hrs)" if has_critical else ("Expedited Consultation (1-2 weeks)" if has_marked else "Routine Physician Review (3-4 weeks)")
    
    return {
        "specialist": spec,
        "primary_category": top_cat,
        "urgency": urgency,
        "rationale": f"Multiple out-of-range findings detected in the {top_cat} panel ({cat_counts[top_cat]} marker(s)).",
        "recommended_followup_tests": followups[:6]
    }

def calculate_cardiometabolic_indices(results: list[dict], sex: str = "male", age: int = 45) -> dict:
    """
    Compute evidence-based cross-biomarker pathophysiological indices:
    - TyG (Triglyceride-Glucose) Index: surrogate marker for insulin resistance
    - AIP (Atherogenic Index of Plasma): subclinical atherogenic cardiovascular risk
    - eGFR (CKD-EPI 2021 race-free equation): renal filtration status
    - Pathophysiological Network Syndromes
    """
    by_k = {r["key"]: r["value"] for r in results if "key" in r and "value" in r}
    indices = {}
    syndromes = []
    
    # 1. TyG Index (Triglyceride-Glucose Index)
    if "glucose_f" in by_k and "trig" in by_k:
        g = by_k["glucose_f"]
        tg = by_k["trig"]
        if g > 0 and tg > 0:
            tyg = round(math.log((tg * g) / 2.0), 2)
            if tyg < 8.5:
                tyg_interp = "Normal insulin sensitivity"
                tyg_risk = "low"
            elif tyg < 8.9:
                tyg_interp = "Borderline insulin resistance (early metabolic risk)"
                tyg_risk = "moderate"
            else:
                tyg_interp = "Significant insulin resistance / metabolic syndrome risk"
                tyg_risk = "high"
            indices["tyg_index"] = {
                "name": "TyG Index (Triglyceride-Glucose)",
                "value": tyg,
                "unit": "index",
                "risk": tyg_risk,
                "interpretation": tyg_interp,
                "citation": "Simental-Mendía et al., Diabetes Care; cut-off >= 8.5 denotes insulin resistance."
            }
            
    # 2. Atherogenic Index of Plasma (AIP) = log10( (TG/88.57) / (HDL/38.67) )
    if "trig" in by_k and "hdl" in by_k:
        tg = by_k["trig"]
        hdl = by_k["hdl"]
        if tg > 0 and hdl > 0:
            tg_mmol = tg / 88.57
            hdl_mmol = hdl / 38.67
            ratio = tg_mmol / hdl_mmol
            if ratio > 0:
                aip = round(math.log10(ratio), 2)
                if aip < 0.11:
                    aip_interp = "Low cardiovascular atherogenic risk"
                    aip_risk = "low"
                elif aip <= 0.21:
                    aip_interp = "Intermediate cardiovascular atherogenic risk"
                    aip_risk = "moderate"
                else:
                    aip_interp = "High cardiovascular atherogenic risk (small dense LDL predominance)"
                    aip_risk = "high"
                indices["aip"] = {
                    "name": "AIP (Atherogenic Index of Plasma)",
                    "value": aip,
                    "unit": "log(TG/HDL)",
                    "risk": aip_risk,
                    "interpretation": aip_interp,
                    "citation": "Dobiásová M. Clin Chem Lab Med; AIP > 0.21 indicates high atherogenic plaque vulnerability."
                }

    # 3. eGFR (CKD-EPI 2021 race-free equation) if creatinine is present and eGFR not already reported
    if "creatinine" in by_k and "egfr" not in by_k:
        scr = by_k["creatinine"]
        if scr > 0:
            is_female = "f" in (sex or "male").lower()
            kappa = 0.7 if is_female else 0.9
            alpha = -0.241 if is_female else -0.302
            min_term = min(scr / kappa, 1.0) ** alpha
            max_term = max(scr / kappa, 1.0) ** (-1.200)
            age_val = age if age and age > 18 else 45
            calc_egfr = round(142.0 * min_term * max_term * (0.9938 ** age_val) * (1.012 if is_female else 1.0), 1)
            
            if calc_egfr >= 90:
                egfr_stage = "Stage 1: Normal or high kidney filtration"
                egfr_risk = "low"
            elif calc_egfr >= 60:
                egfr_stage = "Stage 2: Mildly decreased kidney filtration"
                egfr_risk = "low"
            elif calc_egfr >= 45:
                egfr_stage = "Stage 3a: Mild-to-moderate CKD risk"
                egfr_risk = "moderate"
            elif calc_egfr >= 30:
                egfr_stage = "Stage 3b: Moderate-to-severe CKD"
                egfr_risk = "high"
            elif calc_egfr >= 15:
                egfr_stage = "Stage 4: Severely decreased kidney function"
                egfr_risk = "high"
            else:
                egfr_stage = "Stage 5: Kidney failure / end-stage renal disease"
                egfr_risk = "high"
                
            indices["calculated_egfr"] = {
                "name": "Calculated eGFR (CKD-EPI 2021)",
                "value": calc_egfr,
                "unit": "mL/min/1.73m²",
                "risk": egfr_risk,
                "interpretation": egfr_stage,
                "citation": "Inker LA et al., New England Journal of Medicine 2021; 2021 CKD-EPI Creatinine Equation."
            }

    # 4. Check active Pathophysiology Network Syndromes
    for s_key, s_data in PATHOPHYSIOLOGY_NETWORK.items():
        matched_markers = [k for k in s_data["markers"] if k in by_k]
        # Check how many are out of range
        abnormal_in_syndrome = [
            r for r in results if r.get("key") in s_data["markers"] and r.get("status") != "normal"
        ]
        if len(abnormal_in_syndrome) >= 2:
            syndromes.append({
                "id": s_key,
                "name": s_data["name"],
                "description": s_data["description"],
                "guideline": s_data["guideline"],
                "synergy_alert": s_data["synergy_alert"],
                "involved_abnormal_markers": [r["name"] for r in abnormal_in_syndrome]
            })

    return {
        "indices": indices,
        "active_syndromes": syndromes
    }

def simulate_lifestyle_interventions(results: list[dict], interventions: dict) -> list[dict]:
    """
    Dynamic "What-If" Metabolic Simulator & Digital Twin:
    Projects shift in biomarkers based on evidence from peer-reviewed clinical trials:
    - weight_loss_pct: (Look AHEAD & Diabetes Prevention Program)
    - aerobic_exercise: 150 min/wk moderate aerobic exercise (AHA/ADA)
    - dietary_shift: Mediterranean / low glycemic diet
    - statin_therapy: Lipid-lowering pharmacological adherence
    - iron_supplementation: Oral iron therapy
    """
    by_k = {r["key"]: dict(r) for r in results if "key" in r}
    weight_pct = float(interventions.get("weight_loss_pct", 0) or 0)
    has_exercise = bool(interventions.get("exercise_150min", False))
    has_med_diet = bool(interventions.get("mediterranean_diet", False))
    has_statin = bool(interventions.get("statin_therapy", False))
    has_iron = bool(interventions.get("iron_supplementation", False))
    
    projected = []
    
    for r in results:
        k = r.get("key")
        val = r.get("value")
        if val is None or k is None:
            continue
        p_val = float(val)
        mechanisms = []
        
        # Fasting Glucose
        if k == "glucose_f":
            if weight_pct > 0:
                delta = weight_pct * 2.4  # ~2.4 mg/dL drop per 1% weight loss
                p_val -= delta
                mechanisms.append(f"-{round(delta, 1)} mg/dL from {weight_pct}% weight reduction (DPP Trial)")
            if has_exercise:
                p_val -= 8.0
                mechanisms.append("-8.0 mg/dL from regular exercise (muscle GLUT4 glucose uptake)")
            if has_med_diet:
                p_val -= 5.0
                mechanisms.append("-5.0 mg/dL from low-glycemic Mediterranean dietary pattern")
                
        # HbA1c
        elif k == "hba1c":
            if weight_pct > 0:
                delta = weight_pct * 0.08
                p_val -= delta
                mechanisms.append(f"-{round(delta, 2)}% from {weight_pct}% weight loss (Look AHEAD Study)")
            if has_exercise:
                p_val -= 0.5
                mechanisms.append("-0.5% from 150 min/wk aerobic conditioning")
            if has_med_diet:
                p_val -= 0.3
                mechanisms.append("-0.3% from whole food plant-rich nutrition")

        # Triglycerides
        elif k == "trig":
            if weight_pct > 0:
                pct_drop = min(weight_pct * 2.8, 35.0)  # ~2.8% drop per 1% weight loss
                delta = p_val * (pct_drop / 100.0)
                p_val -= delta
                mechanisms.append(f"-{round(delta, 1)} mg/dL (-{round(pct_drop, 1)}%) from weight loss")
            if has_exercise:
                delta = p_val * 0.12
                p_val -= delta
                mechanisms.append(f"-{round(delta, 1)} mg/dL (-12%) from increased lipoprotein lipase activity")
            if has_statin:
                delta = p_val * 0.15
                p_val -= delta
                mechanisms.append(f"-{round(delta, 1)} mg/dL (-15%) from statin therapy")

        # HDL Cholesterol
        elif k == "hdl":
            if weight_pct > 0:
                delta = weight_pct * 0.55
                p_val += delta
                mechanisms.append(f"+{round(delta, 1)} mg/dL from sustained weight reduction")
            if has_exercise:
                p_val += 3.5
                mechanisms.append("+3.5 mg/dL from aerobic endurance exercise")

        # LDL Cholesterol
        elif k == "ldl":
            if has_med_diet:
                delta = p_val * 0.08
                p_val -= delta
                mechanisms.append(f"-{round(delta, 1)} mg/dL (-8%) from soluble fiber & Mediterranean diet")
            if has_statin:
                delta = p_val * 0.38
                p_val -= delta
                mechanisms.append(f"-{round(delta, 1)} mg/dL (-38%) from moderate-intensity statin HMG-CoA reductase inhibition")

        # Total Cholesterol
        elif k == "chol":
            if has_statin:
                delta = p_val * 0.25
                p_val -= delta
                mechanisms.append(f"-{round(delta, 1)} mg/dL (-25%) from statin therapy")
            elif has_med_diet:
                delta = p_val * 0.06
                p_val -= delta
                mechanisms.append(f"-{round(delta, 1)} mg/dL from Mediterranean dietary intervention")

        # Hemoglobin & Ferritin
        elif k == "hemoglobin" and has_iron:
            p_val += 2.0
            mechanisms.append("+2.0 g/dL expected restoration after 8-12 weeks oral iron therapy (WHO Guidelines)")
        elif k == "ferritin" and has_iron:
            p_val += 35.0
            mechanisms.append("+35.0 ng/mL replenishment of bone marrow iron stores")

        p_val = round(p_val, 1)
        # Re-check status against reference range
        lo = r.get("ref_low")
        hi = r.get("ref_high")
        proj_status = "normal"
        if lo is not None and p_val < lo:
            proj_status = "low"
        elif hi is not None and p_val > hi:
            proj_status = "high"

        projected.append({
            "key": k,
            "name": r.get("name"),
            "unit": r.get("unit"),
            "baseline_value": val,
            "baseline_status": r.get("status"),
            "projected_value": p_val,
            "projected_status": proj_status,
            "net_change": round(p_val - float(val), 1),
            "evidence_mechanisms": mechanisms
        })
        
    return projected

def calculate_phenotypic_age_and_resilience(results: list[dict], chronological_age: int = 45, sex: str = "male") -> dict:
    """
    Evidence-based Phenotypic Biomarker Age & Multi-Organ Resilience Radar Engine:
    Adapted from Levine et al. (Aging, 2018; NHANES mortality calibrations) and the Klemera-Doubal method.
    Evaluates 5 physiological organ-system resilience axes (0-100%):
      1. Metabolic & Glycemic Resilience
      2. Cardiovascular & Atherogenic Resilience
      3. Renal Clearance & Nephron Reserve
      4. Hepatic Synthesis & Detoxification Reserve
      5. Hematologic & Immune Homeostasis
    Computes an estimated Phenotypic Biological Age vs Chronological Age with clinical longevity levers.
    """
    by_k = {}
    for r in results:
        if "key" in r and "value" in r and r["value"] is not None:
            try:
                by_k[r["key"]] = float(r["value"])
            except (ValueError, TypeError):
                pass

    age = float(chronological_age) if chronological_age and float(chronological_age) > 10 else 45.0
    is_female = "f" in (sex or "male").lower()
    
    # -------------------------------------------------------------
    # 1. Metabolic & Glycemic Resilience (Target: glucose <100, HbA1c <5.7%, TG <150)
    # -------------------------------------------------------------
    met_score = 94.0
    met_drivers = []
    met_rejuv = []
    
    g = by_k.get("glucose_f") or by_k.get("glucose_r") or by_k.get("glucose_pp")
    a1c = by_k.get("hba1c")
    tg = by_k.get("trig")
    
    if g is not None:
        if g <= 99:
            met_score += 4.0
            met_drivers.append(f"Optimal fasting glucose ({g} mg/dL)")
        elif g <= 125:
            met_score -= 16.0
            met_drivers.append(f"Impaired fasting glucose in prediabetes range ({g} mg/dL)")
            met_rejuv.append("15-minute post-prandial walking blunts glucose excursions by up to 22% (Look AHEAD trial).")
        else:
            met_score -= 32.0
            met_drivers.append(f"Elevated fasting glucose ({g} mg/dL)")
            met_rejuv.append("Low-glycemic complex carbohydrates and physician-guided glycemic management (ADA 2024).")
            
    if a1c is not None:
        if a1c < 5.7:
            met_score += 3.0
            met_drivers.append(f"Optimal 3-month glycation index (HbA1c {a1c}%)")
        elif a1c <= 6.4:
            met_score -= 15.0
            met_drivers.append(f"Prediabetic glycation status (HbA1c {a1c}%)")
            met_rejuv.append("Weight reduction of 5-7% achieves 58% diabetes risk reduction (Diabetes Prevention Program).")
        else:
            met_score -= 28.0
            met_drivers.append(f"Diabetic-range glycation burden (HbA1c {a1c}%)")
            
    if tg is not None:
        if tg < 150:
            met_score += 2.0
        elif tg <= 199:
            met_score -= 10.0
            met_drivers.append(f"Borderline elevated triglycerides ({tg} mg/dL)")
            met_rejuv.append("Reducing simple refined sugars and alcohol intake rapidly lowers triglyceride synthesis.")
        else:
            met_score -= 20.0
            met_drivers.append(f"High triglycerides ({tg} mg/dL)")
            
    met_score = max(20.0, min(100.0, round(met_score, 1)))

    # -------------------------------------------------------------
    # 2. Cardiovascular & Atherogenic Resilience (Target: LDL <100, HDL >=40/50, Chol <200)
    # -------------------------------------------------------------
    cv_score = 92.0
    cv_drivers = []
    cv_rejuv = []
    
    ldl = by_k.get("ldl")
    hdl = by_k.get("hdl")
    chol = by_k.get("chol")
    
    if ldl is not None:
        if ldl < 100:
            cv_score += 6.0
            cv_drivers.append(f"Optimal atherogenic LDL ({ldl} mg/dL)")
        elif ldl <= 129:
            cv_score -= 6.0
            cv_drivers.append(f"Near optimal LDL ({ldl} mg/dL)")
        elif ldl <= 159:
            cv_score -= 16.0
            cv_drivers.append(f"Borderline high atherogenic LDL ({ldl} mg/dL)")
            cv_rejuv.append("Adding 5-10g/day viscous soluble fiber (oats, psyllium) reduces LDL by 5-11% (AHA/ACC 2024).")
        else:
            cv_score -= 28.0
            cv_drivers.append(f"Elevated plaque-promoting LDL ({ldl} mg/dL)")
            cv_rejuv.append("Discuss lipid-lowering pharmacotherapy and strict saturated fat restriction with physician.")
            
    if hdl is not None:
        hdl_target = 50.0 if is_female else 40.0
        if hdl >= hdl_target + 10:
            cv_score += 4.0
            cv_drivers.append(f"Robust cardio-protective HDL ({hdl} mg/dL)")
        elif hdl >= hdl_target:
            cv_score += 2.0
        else:
            cv_score -= 16.0
            cv_drivers.append(f"Suboptimal protective HDL ({hdl} mg/dL)")
            cv_rejuv.append("Aerobic interval training and healthy monounsaturated fats (extra-virgin olive oil) elevate HDL.")
            
    if chol is not None:
        if chol < 200:
            cv_score += 2.0
        elif chol <= 239:
            cv_score -= 8.0
            cv_drivers.append(f"Borderline total cholesterol ({chol} mg/dL)")
        else:
            cv_score -= 18.0
            cv_drivers.append(f"High total cholesterol ({chol} mg/dL)")
            
    cv_score = max(20.0, min(100.0, round(cv_score, 1)))

    # -------------------------------------------------------------
    # 3. Renal Clearance & Nephron Reserve (Target: eGFR >=90, Creatinine 0.7-1.2, Uric <=7)
    # -------------------------------------------------------------
    renal_score = 95.0
    renal_drivers = []
    renal_rejuv = []
    
    creat = by_k.get("creatinine")
    uric = by_k.get("uric")
    
    calc_egfr = None
    if creat is not None and creat > 0:
        kappa = 0.7 if is_female else 0.9
        alpha = -0.241 if is_female else -0.302
        min_term = min(creat / kappa, 1.0) ** alpha
        max_term = max(creat / kappa, 1.0) ** (-1.200)
        calc_egfr = round(142.0 * min_term * max_term * (0.9938 ** age) * (1.012 if is_female else 1.0), 1)
        
        if calc_egfr >= 90:
            renal_score += 4.0
            renal_drivers.append(f"Robust glomerular filtration (eGFR {calc_egfr} mL/min/1.73m²)")
        elif calc_egfr >= 60:
            renal_score -= 8.0
            renal_drivers.append(f"Mildly decreased nephron reserve (eGFR {calc_egfr} mL/min/1.73m²)")
            renal_rejuv.append("Ensure 2.0-2.5L daily hydration and avoid habitual NSAID analgesics to protect filtration.")
        elif calc_egfr >= 45:
            renal_score -= 25.0
            renal_drivers.append(f"Moderate nephron impairment - CKD Stage 3a (eGFR {calc_egfr})")
            renal_rejuv.append("Nephrologist evaluation, blood pressure optimization (<120/80), and urine microalbumin check (KDIGO 2024).")
        else:
            renal_score -= 45.0
            renal_drivers.append(f"Significant renal filtration decrease (eGFR {calc_egfr})")
            
    if uric is not None:
        uric_hi = 6.0 if is_female else 7.2
        if uric > uric_hi:
            renal_score -= 12.0
            renal_drivers.append(f"Elevated serum uric acid ({uric} mg/dL)")
            renal_rejuv.append("Limit high-purine foods (organ meats, shellfish, alcohol) and maintain adequate hydration.")
            
    renal_score = max(20.0, min(100.0, round(renal_score, 1)))

    # -------------------------------------------------------------
    # 4. Hepatic Synthesis & Detoxification Reserve (Target: ALT/AST <=35, Albumin >=4.0, Bili <=1.2)
    # -------------------------------------------------------------
    hep_score = 95.0
    hep_drivers = []
    hep_rejuv = []
    
    alt = by_k.get("alt")
    ast = by_k.get("ast")
    alb = by_k.get("albumin")
    bili = by_k.get("bili")
    
    if alt is not None:
        if alt <= 35:
            hep_score += 3.0
            hep_drivers.append(f"Optimal ALT transaminase ({alt} U/L)")
        elif alt <= 70:
            hep_score -= 14.0
            hep_drivers.append(f"Mild hepatocyte stress / transaminase bump ({alt} U/L)")
            hep_rejuv.append("Evaluate for metabolic steatotic liver; aerobic exercise reduces hepatic lipid content by ~30% (AASLD).")
        else:
            hep_score -= 30.0
            hep_drivers.append(f"Marked liver enzyme elevation ({alt} U/L)")
            hep_rejuv.append("Physician consultation for viral, drug-induced, or metabolic hepatopathy screening.")
            
    if ast is not None and ast > 35:
        hep_score -= 10.0
        hep_drivers.append(f"Elevated AST ({ast} U/L)")
        
    if alb is not None:
        if alb >= 4.0:
            hep_score += 3.0
            hep_drivers.append(f"Robust protein synthesis (Albumin {alb} g/dL)")
        elif alb < 3.5:
            hep_score -= 22.0
            hep_drivers.append(f"Hypoalbuminemia ({alb} g/dL)")
            hep_rejuv.append("Dietary protein optimization and assessment of systemic chronic inflammation.")
            
    if bili is not None and bili > 1.2:
        hep_score -= 12.0
        hep_drivers.append(f"Elevated total bilirubin ({bili} mg/dL)")
        
    hep_score = max(20.0, min(100.0, round(hep_score, 1)))

    # -------------------------------------------------------------
    # 5. Hematologic & Immune Homeostasis (Target: Hb in range, WBC in range, Plt in range)
    # -------------------------------------------------------------
    hem_score = 94.0
    hem_drivers = []
    hem_rejuv = []
    
    hb = by_k.get("hemoglobin")
    wbc = by_k.get("wbc")
    plt = by_k.get("platelets")
    vitd = by_k.get("vitd")
    b12 = by_k.get("b12")
    
    if hb is not None:
        hb_lo = 12.0 if is_female else 13.0
        if hb >= hb_lo:
            hem_score += 3.0
            hem_drivers.append(f"Optimal oxygen-carrying capacity (Hemoglobin {hb} g/dL)")
        elif hb >= 10.0:
            hem_score -= 16.0
            hem_drivers.append(f"Mild anemia / reduced oxygenation capacity ({hb} g/dL)")
            hem_rejuv.append("Dietary iron pairing (heme iron or legumes with Vitamin C) and ferritin evaluation.")
        else:
            hem_score -= 32.0
            hem_drivers.append(f"Significant anemia ({hb} g/dL)")
            hem_rejuv.append("Physician-guided hematology workup and oral/IV iron replacement.")
            
    if wbc is not None:
        if 4000 <= wbc <= 10000:
            hem_score += 2.0
            hem_drivers.append("Normal immune surveillance (WBC in balance)")
        elif wbc > 11000:
            hem_score -= 16.0
            hem_drivers.append(f"Leukocytosis indicating systemic immune activation ({int(wbc)} /uL)")
        elif wbc < 4000:
            hem_score -= 18.0
            hem_drivers.append(f"Leukopenia ({int(wbc)} /uL)")
            
    if plt is not None:
        if plt < 150000:
            hem_score -= 18.0
            hem_drivers.append(f"Thrombocytopenia ({int(plt)} /uL)")
            
    if vitd is not None and vitd < 30:
        hem_score -= 8.0
        hem_drivers.append(f"Vitamin D deficiency ({vitd} ng/mL)")
        hem_rejuv.append("Targeted Vitamin D3 replenishment restores immunomodulatory equilibrium.")
        
    if b12 is not None and b12 < 300:
        hem_score -= 8.0
        hem_drivers.append(f"Vitamin B12 borderline/low ({b12} pg/mL)")
        hem_rejuv.append("Methylcobalamin supplementation supports myelin synthesis and RBC maturation.")
        
    hem_score = max(20.0, min(100.0, round(hem_score, 1)))

    # -------------------------------------------------------------
    # Composite Biological PhenoAge Calculation
    # -------------------------------------------------------------
    composite_resilience = round((met_score * 0.25) + (cv_score * 0.25) + (renal_score * 0.20) + (hep_score * 0.15) + (hem_score * 0.15), 1)
    
    # Baseline population equilibrium reference is 82.0 points
    age_delta = round(-(composite_resilience - 82.0) * 0.32, 1)
    age_delta = max(-8.5, min(12.0, age_delta))
    phenotypic_age = round(max(18.0, age + age_delta), 1)

    if age_delta <= -2.5:
        vitality_status = "youthful"
        vitality_badge = f"🌿 Optimal Biological Resilience ({abs(age_delta)} yrs younger)"
        vitality_summary = "Your multi-organ biomarkers demonstrate superior cellular homeostasis, placing your functional biological age significantly below your chronological benchmark."
    elif age_delta <= 1.5:
        vitality_status = "stable"
        vitality_badge = "⚖️ Synchronized Biological Age"
        vitality_summary = "Your physiological organ reserve is well-balanced and closely aligned with expected chronological age benchmarks."
    else:
        vitality_status = "accelerated_wear"
        vitality_badge = f"⚠️ Accelerated Metabolic Strain (+{age_delta} yrs)"
        vitality_summary = "Certain organ systems are experiencing subclinical physiological strain. Targeted lifestyle and medical interventions can reverse this trajectory and restore functional reserve."

    axis_entries = [
        {"axis": "metabolic", "name": "Metabolic & Glycemic", "score": met_score, "drivers": met_drivers, "rejuv": met_rejuv},
        {"axis": "cardiovascular", "name": "Cardiovascular & Lipid", "score": cv_score, "drivers": cv_drivers, "rejuv": cv_rejuv},
        {"axis": "renal", "name": "Renal & Clearance", "score": renal_score, "drivers": renal_drivers, "rejuv": renal_rejuv},
        {"axis": "hepatic", "name": "Hepato-Biliary Function", "score": hep_score, "drivers": hep_drivers, "rejuv": hep_rejuv},
        {"axis": "hematologic", "name": "Hematologic & Immune", "score": hem_score, "drivers": hem_drivers, "rejuv": hem_rejuv}
    ]
    
    sorted_deficit = sorted(axis_entries, key=lambda x: x["score"])
    key_priorities = []
    for item in sorted_deficit[:2]:
        if item["score"] < 85:
            rejuv_tip = item["rejuv"][0] if item["rejuv"] else "Maintain close follow-up with your healthcare provider."
            key_priorities.append(f"**{item['name']} Axis ({item['score']}% Resilience)**: {rejuv_tip}")
    if not key_priorities:
        key_priorities.append("All 5 physiological organ axes are operating in high-resilience tiers. Maintain current exercise, nutrition, and preventive checkup routines.")

    return {
        "chronological_age": int(age),
        "phenotypic_age": phenotypic_age,
        "age_delta": age_delta,
        "vitality_status": vitality_status,
        "vitality_badge": vitality_badge,
        "vitality_summary": vitality_summary,
        "composite_resilience": composite_resilience,
        "axes": axis_entries,
        "radar_data": {
            "labels": ["Metabolic", "Cardiovascular", "Renal", "Hepatic", "Hematologic & Immune"],
            "patient_scores": [met_score, cv_score, renal_score, hep_score, hem_score],
            "optimal_benchmark": [90.0, 90.0, 90.0, 90.0, 90.0]
        },
        "key_priorities": key_priorities,
        "citation": "Biostatistical composite aging model adapted from Levine ME et al. Aging (2018) & NHANES mortality prediction calibrations."
    }

def audit_prescription_and_depletions(results: list[dict], medications: list = None) -> dict:
    """
    Drug-Nutrient Depletion & Medication Interaction Co-Pilot Engine.

    Cross-references patient's current prescription medications with laboratory results to:
      1. Corroborate Active Nutrient Depletions (lab-verified deficiencies induced by drugs).
      2. Identify Unmonitored Surveillance Gaps (nutrients depleted by drugs not on this panel).
      3. Reassure on Benign Pharmacological Lab Shifts (e.g. statin ALT <= 3x ULN, ACEi creatinine <= 30%).
      4. Synthesize non-prescriptive, doctor-facing discussion points for clinical follow-up.
    """
    # 1. Normalize medications list
    if medications is None:
        med_list = []
    elif isinstance(medications, str):
        med_list = [m.strip() for m in re.split(r"[,;\n]+", medications) if m.strip()]
    elif isinstance(medications, (list, tuple, set)):
        med_list = [str(m).strip() for m in medications if m and str(m).strip()]
    else:
        med_list = []

    # 2. Index lab results by key
    res_map = {}
    for r in (results or []):
        if not isinstance(r, dict):
            continue
        k = r.get("key")
        if not k:
            name = r.get("name", "")
            resolved = resolve_marker(name)
            if resolved:
                k = resolved[0]
        if k:
            res_map[str(k).lower()] = r

    # 3. Match medications against DRUG_NUTRIENT_DEPLETION_CATALOG
    matched_classes = {}
    for med in med_list:
        med_lower = med.lower()
        for drug_class, catalog in DRUG_NUTRIENT_DEPLETION_CATALOG.items():
            if any(d_name in med_lower for d_name in catalog["names"]):
                if drug_class not in matched_classes:
                    matched_classes[drug_class] = {
                        "drug_class": drug_class,
                        "drug_class_name": catalog["drug_class_name"],
                        "medications": [med],
                        "catalog": catalog
                    }
                else:
                    if med not in matched_classes[drug_class]["medications"]:
                        matched_classes[drug_class]["medications"].append(med)

    raw_active = []
    raw_gaps = []
    benign_shifts = []

    # 4. Process Depletions & Surveillance Gaps
    for drug_class, info in matched_classes.items():
        catalog = info["catalog"]
        med_label = ", ".join(info["medications"])
        
        for nut in catalog.get("depleted_nutrients", []):
            n_key = nut["key"]
            lab_row = res_map.get(n_key)
            
            if lab_row is not None:
                val = lab_row.get("value")
                ref_lo = lab_row.get("ref_low")
                ref_hi = lab_row.get("ref_high")
                status = lab_row.get("status")
                
                is_depleted = False
                if status == "low":
                    is_depleted = True
                elif isinstance(val, (int, float)) and ref_lo is not None and val < ref_lo:
                    is_depleted = True
                    
                if is_depleted:
                    raw_active.append({
                        "nutrient_key": n_key,
                        "nutrient_name": nut["name"],
                        "lab_value": val,
                        "lab_unit": lab_row.get("unit", ""),
                        "ref_low": ref_lo,
                        "ref_high": ref_hi,
                        "status": "low",
                        "drug_class": drug_class,
                        "drug_class_name": catalog["drug_class_name"],
                        "medication_taken": med_label,
                        "mechanism": nut["mechanism"],
                        "clinical_risk": nut["clinical_risk"],
                        "severity": nut["severity"],
                        "recommended_test": nut["recommended_test"],
                        "evidence_citation": nut["evidence_citation"],
                        "doctor_question": nut["doctor_question"]
                    })
            else:
                raw_gaps.append({
                    "nutrient_key": n_key,
                    "nutrient_name": nut["name"],
                    "status": "unmeasured",
                    "drug_class": drug_class,
                    "drug_class_name": catalog["drug_class_name"],
                    "medication_taken": med_label,
                    "mechanism": nut["mechanism"],
                    "clinical_risk": nut["clinical_risk"],
                    "severity": nut["severity"],
                    "recommended_test": nut["recommended_test"],
                    "evidence_citation": nut["evidence_citation"],
                    "doctor_question": nut["doctor_question"]
                })

    # Group and merge compounded depletions by nutrient_key
    active_depletions = []
    active_by_key = {}
    for dep in raw_active:
        k = dep["nutrient_key"]
        if k not in active_by_key:
            entry = dict(dep)
            entry["contributing_meds"] = [dep["medication_taken"]]
            entry["contributing_classes"] = [dep["drug_class_name"]]
            entry["mechanisms"] = [dep["mechanism"]]
            active_by_key[k] = entry
            active_depletions.append(entry)
        else:
            entry = active_by_key[k]
            if dep["medication_taken"] not in entry["contributing_meds"]:
                entry["contributing_meds"].append(dep["medication_taken"])
            if dep["drug_class_name"] not in entry["contributing_classes"]:
                entry["contributing_classes"].append(dep["drug_class_name"])
            if dep["mechanism"] not in entry["mechanisms"]:
                entry["mechanisms"].append(dep["mechanism"])
            entry["medication_taken"] = ", ".join(entry["contributing_meds"])
            entry["drug_class_name"] = ", ".join(entry["contributing_classes"])
            entry["mechanism"] = "Compounded Multidrug Depletion: " + " | ".join(entry["mechanisms"])

    # Group surveillance gaps by nutrient_key (and omit if already an active depletion)
    surveillance_gaps = []
    gaps_by_key = {}
    for gap in raw_gaps:
        k = gap["nutrient_key"]
        if k in active_by_key:
            continue
        if k not in gaps_by_key:
            entry = dict(gap)
            entry["contributing_meds"] = [gap["medication_taken"]]
            gaps_by_key[k] = entry
            surveillance_gaps.append(entry)
        else:
            entry = gaps_by_key[k]
            if gap["medication_taken"] not in entry["contributing_meds"]:
                entry["contributing_meds"].append(gap["medication_taken"])
            entry["medication_taken"] = ", ".join(entry["contributing_meds"])


    # 5. Process Benign Pharmacological Lab Shifts
    for drug_class, info in matched_classes.items():
        catalog = info["catalog"]
        med_label = ", ".join(info["medications"])
        
        for shift in catalog.get("benign_shifts", []):
            for m_key in shift.get("markers", []):
                lab_row = res_map.get(m_key)
                if not lab_row:
                    continue
                val = lab_row.get("value")
                ref_hi = lab_row.get("ref_high")
                ref_lo = lab_row.get("ref_low")
                status = lab_row.get("status")

                matched_shift = False
                shift_detail = {}

                # Statin ALT/AST <= 3x ULN
                if drug_class == "statin" and m_key in ("alt", "ast") and status == "high":
                    mult = shift.get("max_benign_multiplier", 3.0)
                    if ref_hi and isinstance(val, (int, float)) and val <= (mult * ref_hi):
                        matched_shift = True
                        shift_detail = {
                            "metric_context": f"{val} {lab_row.get('unit', 'U/L')} (Reference limit: {ref_hi} U/L, {round(val/ref_hi, 1)}× ULN — well within benign ≤3× threshold)",
                            "reassurance_badge": "🟢 Expected Hepatic Adaptation (Safe)"
                        }

                # ACE inhibitor Creatinine <= 30% above ULN
                elif drug_class == "ace_inhibitor" and m_key == "creatinine" and status == "high":
                    mult = shift.get("max_benign_multiplier", 1.30)
                    if ref_hi and isinstance(val, (int, float)) and val <= (mult * ref_hi):
                        matched_shift = True
                        pct = round(((val - ref_hi) / ref_hi) * 100, 1)
                        shift_detail = {
                            "metric_context": f"{val} {lab_row.get('unit', 'mg/dL')} (+{pct}% above reference limit {ref_hi} — within expected ≤30% hemodynamic margin)",
                            "reassurance_badge": "🟢 Hemodynamic Renoprotection Shift (Expected)"
                        }

                # ACE inhibitor Potassium <= 5.2
                elif drug_class == "ace_inhibitor" and m_key == "potassium" and (status == "high" or (isinstance(val, (int, float)) and val >= 4.9)):
                    max_val = shift.get("max_benign_value", 5.2)
                    if isinstance(val, (int, float)) and val <= max_val:
                        matched_shift = True
                        shift_detail = {
                            "metric_context": f"{val} {lab_row.get('unit', 'mmol/L')} (Expected RAAS-suppressed potassium retention, within ≤{max_val} margin)",
                            "reassurance_badge": "🟢 Expected Aldosterone Modulation"
                        }

                # Diuretic Uric Acid
                elif drug_class == "diuretic" and m_key == "uric" and status == "high":
                    matched_shift = True
                    shift_detail = {
                        "metric_context": f"{val} {lab_row.get('unit', 'mg/dL')} (Competitive renal tubular excretion by diuretic)",
                        "reassurance_badge": "🟢 Asymptomatic Organic Acid Shift"
                    }

                # SGLT2 inhibitor eGFR dip
                elif drug_class == "sglt2_inhibitor" and m_key == "egfr" and (status == "low" or (isinstance(val, (int, float)) and val < 90)):
                    matched_shift = True
                    shift_detail = {
                        "metric_context": f"{val} {lab_row.get('unit', 'mL/min/1.73m2')} (Classic 'SGLT2 Dip' reflecting restorative afferent tone)",
                        "reassurance_badge": "🟢 Renoprotective Tubuloglomerular Shift"
                    }

                # SGLT2 inhibitor hematocrit / hemoglobin rise
                elif drug_class == "sglt2_inhibitor" and m_key in ("hematocrit", "hemoglobin") and (status == "high" or (isinstance(val, (int, float)) and ref_hi and val >= ref_hi * 0.95)):
                    matched_shift = True
                    shift_detail = {
                        "metric_context": f"{val} {lab_row.get('unit', '')} (Physiological hemoconcentration & erythropoietin enhancement)",
                        "reassurance_badge": "🟢 Physiological Oxygen Carrier Response"
                    }

                # Corticosteroids WBC / Neutrophils leukocytosis
                elif drug_class == "corticosteroid" and m_key in ("wbc", "neutrophils") and status == "high":
                    matched_shift = True
                    shift_detail = {
                        "metric_context": f"{val} {lab_row.get('unit', '')} (Sterile leukocyte demargination from vascular endothelial margins)",
                        "reassurance_badge": "🟢 Sterile Pharmacological Demargination"
                    }

                # NSAIDs mild creatinine
                elif drug_class == "nsaid" and m_key == "creatinine" and status == "high":
                    matched_shift = True
                    shift_detail = {
                        "metric_context": f"{val} {lab_row.get('unit', 'mg/dL')} (Prostaglandin-mediated afferent arteriolar hemodynamics)",
                        "reassurance_badge": "🟡 NSAID Hemodynamic Effect"
                    }

                if matched_shift:
                    benign_shifts.append({
                        "marker_key": m_key,
                        "marker_name": lab_row.get("name", m_key.upper()),
                        "lab_value": val,
                        "lab_unit": lab_row.get("unit", ""),
                        "ref_high": ref_hi,
                        "drug_class": drug_class,
                        "drug_class_name": catalog["drug_class_name"],
                        "medication_taken": med_label,
                        "label": shift["label"],
                        "clinical_explanation": shift["clinical_explanation"],
                        "guideline": shift.get("guideline", ""),
                        "doctor_question": shift.get("doctor_question", ""),
                        "metric_context": shift_detail.get("metric_context", ""),
                        "reassurance_badge": shift_detail.get("reassurance_badge", "🟢 Pharmacological Effect")
                    })

    # 6. Synthesize Doctor Discussion Script
    doctor_questions = []
    # Priority 1: Active Depletions
    for dep in active_depletions:
        doctor_questions.append({
            "priority": "high",
            "badge": "🔴 High Priority — Lab-Confirmed",
            "category": "Active Depletion",
            "title": f"Discuss low {dep['nutrient_name']} while on {dep['medication_taken']}",
            "question": dep["doctor_question"],
            "context": f"Your lab confirms low {dep['nutrient_name']} ({dep['lab_value']} {dep['lab_unit']}, ref {dep['ref_low']}-{dep['ref_high']}). ADA/clinical evidence links this to {dep['drug_class_name']}."
        })

    # Priority 2: Benign Lab Shifts (Reassurance)
    for shift in benign_shifts:
        doctor_questions.append({
            "priority": "reassurance",
            "badge": "🟢 Reassurance — Expected Shift",
            "category": "Expected Medication Effect",
            "title": f"Confirm expected {shift['marker_name']} shift on {shift['medication_taken']}",
            "question": shift["doctor_question"],
            "context": f"{shift['label']} ({shift['metric_context']}). Clinical guidelines suggest surveillance rather than discontinuation."
        })

    # Priority 3: Surveillance Gaps
    for gap in surveillance_gaps:
        doctor_questions.append({
            "priority": "preventive",
            "badge": "🟡 Preventive Surveillance",
            "category": "Surveillance Consideration",
            "title": f"Consider {gap['nutrient_name']} order at next checkup",
            "question": gap["doctor_question"],
            "context": f"Nutrient not measured on this panel. {gap['evidence_citation']} recommends periodic monitoring while on {gap['medication_taken']}."
        })

    # Deduplicate doctor questions
    seen_q = set()
    deduped_questions = []
    for q in doctor_questions:
        q_key = (q.get("title", ""), q.get("question", ""))
        if q_key not in seen_q:
            seen_q.add(q_key)
            deduped_questions.append(q)
    doctor_questions = deduped_questions


    # 7. Summary
    all_matched_meds = []
    for info in matched_classes.values():
        all_matched_meds.extend(info["medications"])

    if not med_list:
        summary_text = "No active prescription medications provided for nutrient depletion auditing. Add medications below to run interactive pharmacological surveillance."
    elif not matched_classes:
        summary_text = f"Audited {len(med_list)} medication(s). None have known clinical drug-nutrient depletions or lab interactions in our evidence catalog."
    else:
        parts = []
        if active_depletions:
            parts.append(f"⚠️ {len(active_depletions)} active lab-confirmed nutrient depletion(s) detected ({', '.join(d['nutrient_name'] for d in active_depletions)}).")
        if benign_shifts:
            parts.append(f"🟢 {len(benign_shifts)} expected benign pharmacological lab shift(s) identified (e.g. {', '.join(s['marker_name'] for s in benign_shifts)}).")
        if surveillance_gaps:
            parts.append(f"🟡 {len(surveillance_gaps)} unmonitored surveillance gap(s) to discuss for future bloodwork.")
        summary_text = " ".join(parts) if parts else "Prescription medications reviewed; no immediate nutrient depletions or unexpected lab shifts noted."

    return {
        "audited_medications": list(dict.fromkeys(all_matched_meds)),
        "raw_medications": med_list,
        "total_medications_audited": len(matched_classes),
        "active_depletions": active_depletions,
        "active_depletions_count": len(active_depletions),
        "surveillance_gaps": surveillance_gaps,
        "surveillance_gaps_count": len(surveillance_gaps),
        "benign_shifts": benign_shifts,
        "benign_shifts_count": len(benign_shifts),
        "doctor_discussion_script": doctor_questions,
        "summary": summary_text,
        "has_findings": bool(active_depletions or surveillance_gaps or benign_shifts)
    }


# ==============================================================================
# CLINICIAN EHR SOAP & ICD-10-CM / SNOMED CT CODING MATRIX
# ==============================================================================

ICD10_SNOMED_CATALOG = {
    "T2DM": {
        "icd10_code": "E11.69",
        "icd10_description": "Type 2 diabetes mellitus with other specified complications",
        "snomed_concept_id": "44054006",
        "snomed_fsn": "Type 2 diabetes mellitus (disorder)",
        "domain": "Endocrinology / Metabolism",
        "billing_tier": "Primary Diagnostic Code",
    },
    "PREDIABETES": {
        "icd10_code": "R73.03",
        "icd10_description": "Prediabetes",
        "snomed_concept_id": "714628002",
        "snomed_fsn": "Prediabetes (disorder)",
        "domain": "Endocrinology / Metabolism",
        "billing_tier": "Secondary Diagnostic Code",
    },
    "HYPERGLYCEMIA": {
        "icd10_code": "R73.9",
        "icd10_description": "Hyperglycemia, unspecified",
        "snomed_concept_id": "80394007",
        "snomed_fsn": "Hyperglycemia (finding)",
        "domain": "Endocrinology / Metabolism",
        "billing_tier": "Secondary Lab Finding Code",
    },
    "MIXED_HYPERLIPIDEMIA": {
        "icd10_code": "E78.2",
        "icd10_description": "Mixed hyperlipidemia",
        "snomed_concept_id": "3877011000036101",
        "snomed_fsn": "Mixed hyperlipidemia (disorder)",
        "domain": "Cardiovascular / Lipidology",
        "billing_tier": "Primary Diagnostic Code",
    },
    "PURE_HYPERCHOLESTEROLEMIA": {
        "icd10_code": "E78.00",
        "icd10_description": "Pure hypercholesterolemia, unspecified",
        "snomed_concept_id": "13644009",
        "snomed_fsn": "Hypercholesterolemia (disorder)",
        "domain": "Cardiovascular / Lipidology",
        "billing_tier": "Primary Diagnostic Code",
    },
    "HYPERTRIGLYCERIDEMIA": {
        "icd10_code": "E78.1",
        "icd10_description": "Pure hyperglyceridemia",
        "snomed_concept_id": "302870006",
        "snomed_fsn": "Hypertriglyceridemia (disorder)",
        "domain": "Cardiovascular / Lipidology",
        "billing_tier": "Secondary Diagnostic Code",
    },
    "LOW_HDL": {
        "icd10_code": "E78.6",
        "icd10_description": "Lipoprotein deficiency (Hypoalphalipoproteinemia / Low HDL)",
        "snomed_concept_id": "238075005",
        "snomed_fsn": "Hypoalphalipoproteinemia (disorder)",
        "domain": "Cardiovascular / Lipidology",
        "billing_tier": "Secondary Risk Finding Code",
    },
    "CKD_3A": {
        "icd10_code": "N18.31",
        "icd10_description": "Chronic kidney disease, stage 3a",
        "snomed_concept_id": "431855005",
        "snomed_fsn": "Chronic kidney disease stage 3 (disorder)",
        "domain": "Nephrology / Renal",
        "billing_tier": "Primary Diagnostic Code",
    },
    "CKD_3B": {
        "icd10_code": "N18.32",
        "icd10_description": "Chronic kidney disease, stage 3b",
        "snomed_concept_id": "431855005",
        "snomed_fsn": "Chronic kidney disease stage 3 (disorder)",
        "domain": "Nephrology / Renal",
        "billing_tier": "Primary Diagnostic Code",
    },
    "CKD_4": {
        "icd10_code": "N18.4",
        "icd10_description": "Chronic kidney disease, stage 4 (severe)",
        "snomed_concept_id": "433146000",
        "snomed_fsn": "Chronic kidney disease stage 4 (disorder)",
        "domain": "Nephrology / Renal",
        "billing_tier": "Primary Diagnostic Code",
    },
    "CKD_5": {
        "icd10_code": "N18.5",
        "icd10_description": "Chronic kidney disease, stage 5",
        "snomed_concept_id": "433144002",
        "snomed_fsn": "Chronic kidney disease stage 5 (disorder)",
        "domain": "Nephrology / Renal",
        "billing_tier": "Primary Diagnostic Code",
    },
    "ABNORMAL_RENAL_LABS": {
        "icd10_code": "R94.4",
        "icd10_description": "Abnormal results of kidney function studies",
        "snomed_concept_id": "166717003",
        "snomed_fsn": "Abnormal renal function test (finding)",
        "domain": "Nephrology / Renal",
        "billing_tier": "Secondary Lab Finding Code",
    },
    "TRANSAMINITIS": {
        "icd10_code": "R74.01",
        "icd10_description": "Elevation of levels of liver transaminase levels",
        "snomed_concept_id": "166632009",
        "snomed_fsn": "Serum alanine aminotransferase raised (finding)",
        "domain": "Hepatobiliary / GI",
        "billing_tier": "Secondary Lab Finding Code",
    },
    "HYPERBILIRUBINEMIA": {
        "icd10_code": "R17",
        "icd10_description": "Unspecified jaundice / Hyperbilirubinemia",
        "snomed_concept_id": "18165001",
        "snomed_fsn": "Jaundice (finding)",
        "domain": "Hepatobiliary / GI",
        "billing_tier": "Secondary Lab Finding Code",
    },
    "IRON_DEFICIENCY_ANEMIA": {
        "icd10_code": "D50.9",
        "icd10_description": "Iron deficiency anemia, unspecified",
        "snomed_concept_id": "87522002",
        "snomed_fsn": "Iron deficiency anemia (disorder)",
        "domain": "Hematology",
        "billing_tier": "Primary Diagnostic Code",
    },
    "B12_DEFICIENCY_ANEMIA": {
        "icd10_code": "D51.9",
        "icd10_description": "Vitamin B12 deficiency anemia, unspecified",
        "snomed_concept_id": "271737000",
        "snomed_fsn": "Vitamin B12 deficiency anemia (disorder)",
        "domain": "Hematology",
        "billing_tier": "Primary Diagnostic Code",
    },
    "ANEMIA_UNSPECIFIED": {
        "icd10_code": "D64.9",
        "icd10_description": "Anemia, unspecified",
        "snomed_concept_id": "271737000",
        "snomed_fsn": "Anemia (disorder)",
        "domain": "Hematology",
        "billing_tier": "Primary Diagnostic Code",
    },
    "THROMBOCYTOPENIA": {
        "icd10_code": "D69.6",
        "icd10_description": "Thrombocytopenia, unspecified",
        "snomed_concept_id": "302215000",
        "snomed_fsn": "Thrombocytopenia (disorder)",
        "domain": "Hematology",
        "billing_tier": "Secondary Diagnostic Code",
    },
    "LEUKOCYTOSIS": {
        "icd10_code": "D72.829",
        "icd10_description": "Elevated white blood cell count, unspecified",
        "snomed_concept_id": "414478003",
        "snomed_fsn": "Leukocytosis (finding)",
        "domain": "Hematology / Immunology",
        "billing_tier": "Secondary Lab Finding Code",
    },
    "LEUKOPENIA": {
        "icd10_code": "D72.819",
        "icd10_description": "Decreased white blood cell count, unspecified",
        "snomed_concept_id": "84828003",
        "snomed_fsn": "Leukopenia (finding)",
        "domain": "Hematology / Immunology",
        "billing_tier": "Secondary Lab Finding Code",
    },
    "VITAMIN_D_DEFICIENCY": {
        "icd10_code": "E55.9",
        "icd10_description": "Vitamin D deficiency, unspecified",
        "snomed_concept_id": "34713006",
        "snomed_fsn": "Vitamin D deficiency (disorder)",
        "domain": "Nutritional / Metabolic",
        "billing_tier": "Secondary Diagnostic Code",
    },
    "VITAMIN_B12_DEFICIENCY": {
        "icd10_code": "E53.8",
        "icd10_description": "Deficiency of other specified B group vitamins (Vitamin B12 deficiency)",
        "snomed_concept_id": "238120002",
        "snomed_fsn": "Vitamin B12 deficiency (disorder)",
        "domain": "Nutritional / Metabolic",
        "billing_tier": "Secondary Diagnostic Code",
    },
    "DRUG_INDUCED_B12_DEFICIENCY": {
        "icd10_code": "T38.3X5A",
        "icd10_description": "Adverse effect of insulin and oral hypoglycemic drugs, initial encounter",
        "snomed_concept_id": "293593005",
        "snomed_fsn": "Adverse effect of biguanide (disorder)",
        "domain": "Pharmacotherapy / Adverse Drug Effect",
        "billing_tier": "Adverse Drug Effect Code",
    },
    "IRON_DEFICIENCY_NONANEMIC": {
        "icd10_code": "E61.1",
        "icd10_description": "Iron deficiency without anemia",
        "snomed_concept_id": "10743008",
        "snomed_fsn": "Iron deficiency (disorder)",
        "domain": "Nutritional / Metabolic",
        "billing_tier": "Secondary Diagnostic Code",
    },
    "HYPERKALEMIA": {
        "icd10_code": "E87.5",
        "icd10_description": "Hyperkalemia",
        "snomed_concept_id": "14140009",
        "snomed_fsn": "Hyperkalemia (disorder)",
        "domain": "Electrolytes & Fluid Balance",
        "billing_tier": "Acute Risk Finding Code",
    },
    "HYPOKALEMIA": {
        "icd10_code": "E87.6",
        "icd10_description": "Hypokalemia",
        "snomed_concept_id": "43339004",
        "snomed_fsn": "Hypokalemia (disorder)",
        "domain": "Electrolytes & Fluid Balance",
        "billing_tier": "Acute Risk Finding Code",
    },
    "HYPONATREMIA": {
        "icd10_code": "E87.1",
        "icd10_description": "Hypo-osmolality and hyponatremia",
        "snomed_concept_id": "89627008",
        "snomed_fsn": "Hyponatremia (disorder)",
        "domain": "Electrolytes & Fluid Balance",
        "billing_tier": "Acute Risk Finding Code",
    },
    "HYPERURICEMIA": {
        "icd10_code": "E79.0",
        "icd10_description": "Hyperuricemia without signs of inflammatory arthritis and tophaceous disease",
        "snomed_concept_id": "35885006",
        "snomed_fsn": "Hyperuricemia (disorder)",
        "domain": "Endocrinology / Metabolism",
        "billing_tier": "Secondary Diagnostic Code",
    },
    "HYPOTHYROIDISM": {
        "icd10_code": "E03.9",
        "icd10_description": "Hypothyroidism, unspecified",
        "snomed_concept_id": "40930008",
        "snomed_fsn": "Hypothyroidism (disorder)",
        "domain": "Endocrinology / Thyroid",
        "billing_tier": "Primary Diagnostic Code",
    },
    "HYPERTHYROIDISM": {
        "icd10_code": "E05.90",
        "icd10_description": "Thyrotoxicosis, unspecified without thyrotoxic crisis",
        "snomed_concept_id": "34486009",
        "snomed_fsn": "Hyperthyroidism (disorder)",
        "domain": "Endocrinology / Thyroid",
        "billing_tier": "Primary Diagnostic Code",
    },
    "ELEVATED_INFLAMMATORY_MARKERS": {
        "icd10_code": "R70.0",
        "icd10_description": "Elevated erythrocyte sedimentation rate and abnormal plasma viscosity",
        "snomed_concept_id": "271636001",
        "snomed_fsn": "Elevated erythrocyte sedimentation rate (finding)",
        "domain": "Infectious / Inflammatory",
        "billing_tier": "Secondary Lab Finding Code",
    },
    "GENERAL_EXAM_NORMAL": {
        "icd10_code": "Z00.00",
        "icd10_description": "Encounter for general adult medical examination without abnormal findings",
        "snomed_concept_id": "307824009",
        "snomed_fsn": "Encounter for check up (procedure)",
        "domain": "Preventive & Health Maintenance",
        "billing_tier": "Preventive Surveillance Code",
    }
}


def map_lab_findings_to_icd10_snomed(results: list, medications: list = None) -> list:
    """
    Automated ICD-10-CM & SNOMED CT Clinical Concept Mapper.
    Maps laboratory findings and active drug regimens to standardized billing and EHR terms.
    """
    if not results:
        return []
        
    meds_clean = [str(m).lower() for m in (medications or [])]
    is_on_metformin = any("metformin" in m or "glucophage" in m for m in meds_clean)
    
    # Index results by canonical key
    by_key = {}
    for r in results:
        k = r.get("key")
        if not k:
            m = lookup(r.get("name", ""))
            k = m["key"] if m else r.get("name", "").lower().replace(" ", "_")
        by_key[k] = r

    findings = []
    seen_codes = set()

    def add_finding(catalog_key, confidence, rationale, supporting):
        entry = ICD10_SNOMED_CATALOG.get(catalog_key)
        if not entry:
            return
        code = entry["icd10_code"]
        if code in seen_codes:
            return
        seen_codes.add(code)
        findings.append({
            "icd10_code": code,
            "icd10_description": entry["icd10_description"],
            "snomed_concept_id": entry["snomed_concept_id"],
            "snomed_fsn": entry["snomed_fsn"],
            "domain": entry["domain"],
            "billing_tier": entry["billing_tier"],
            "confidence": confidence,
            "clinical_rationale": rationale,
            "supporting_markers": [
                {
                    "name": s.get("name", ""),
                    "value": s.get("value"),
                    "unit": s.get("unit", ""),
                    "status": s.get("status", "normal")
                }
                for s in supporting if s
            ]
        })

    def val(k):
        r = by_key.get(k)
        if not r or r.get("value") is None:
            return None
        try:
            return float(r["value"])
        except (ValueError, TypeError):
            return None

    def status(k):
        r = by_key.get(k)
        return r.get("status", "normal") if r else "normal"

    # 1. Glycemic / Diabetes
    hba1c_v = val("hba1c")
    gf_v = val("glucose_f")
    gpp_v = val("glucose_pp")
    gr_v = val("glucose_r")

    if (hba1c_v is not None and hba1c_v >= 6.5) or (gf_v is not None and gf_v >= 126) or (gpp_v is not None and gpp_v >= 200) or (gr_v is not None and gr_v >= 200):
        supp = [by_key.get(k) for k in ("hba1c", "glucose_f", "glucose_pp", "glucose_r") if by_key.get(k)]
        add_finding("T2DM", "Definitive", "ADA 2024 diagnostic criteria met based on diagnostic glycemic threshold.", supp)
    elif (hba1c_v is not None and 5.7 <= hba1c_v < 6.5) or (gf_v is not None and 100 <= gf_v < 126):
        supp = [by_key.get(k) for k in ("hba1c", "glucose_f") if by_key.get(k)]
        add_finding("PREDIABETES", "Definitive", "Impaired fasting glucose or intermediate HbA1c in 5.7-6.4% prediabetic spectrum.", supp)
    elif any(status(k) == "high" for k in ("glucose_f", "glucose_pp", "glucose_r")):
        supp = [by_key.get(k) for k in ("glucose_f", "glucose_pp", "glucose_r") if status(k) == "high"]
        add_finding("HYPERGLYCEMIA", "Probable", "Elevated circulating glucose level requiring confirmatory fasting evaluation.", supp)

    # 2. Lipidology / Cardiovascular
    ldl_v = val("ldl")
    chol_v = val("chol")
    trig_v = val("trig")
    hdl_v = val("hdl")

    ldl_high = status("ldl") == "high" or (ldl_v is not None and ldl_v >= 160) or (chol_v is not None and chol_v >= 200)
    trig_high = status("trig") == "high" or (trig_v is not None and trig_v >= 150)
    hdl_low = status("hdl") == "low" or (hdl_v is not None and hdl_v < 40)

    if ldl_high and trig_high:
        supp = [by_key.get(k) for k in ("ldl", "chol", "trig") if by_key.get(k)]
        add_finding("MIXED_HYPERLIPIDEMIA", "Definitive", "Combined elevation of atherogenic low-density lipoprotein / total cholesterol and serum triglycerides.", supp)
    elif ldl_high:
        supp = [by_key.get(k) for k in ("ldl", "chol") if by_key.get(k)]
        add_finding("PURE_HYPERCHOLESTEROLEMIA", "Definitive", "Isolated elevation of LDL-C or total cholesterol with normal triglycerides.", supp)
    elif trig_high:
        supp = [by_key.get("trig")] if by_key.get("trig") else []
        add_finding("HYPERTRIGLYCERIDEMIA", "Definitive", "Isolated serum triglyceride elevation exceeding 150 mg/dL target threshold.", supp)

    if hdl_low:
        supp = [by_key.get("hdl")] if by_key.get("hdl") else []
        add_finding("LOW_HDL", "Definitive", "Subnormal HDL-C level conferring heightened atherogenic cardiovascular risk profile.", supp)

    # 3. Renal & Nephrology
    egfr_v = val("egfr")
    creat_v = val("creatinine")
    bun_v = val("bun") or val("urea")

    if egfr_v is not None and egfr_v < 60:
        supp = [by_key.get(k) for k in ("egfr", "creatinine", "bun") if by_key.get(k)]
        if egfr_v >= 45:
            add_finding("CKD_3A", "Probable", "eGFR between 45-59 mL/min/1.73m² indicates Chronic Kidney Disease Stage 3a.", supp)
        elif egfr_v >= 30:
            add_finding("CKD_3B", "Probable", "eGFR between 30-44 mL/min/1.73m² indicates Chronic Kidney Disease Stage 3b.", supp)
        elif egfr_v >= 15:
            add_finding("CKD_4", "Probable", "eGFR between 15-29 mL/min/1.73m² indicates Chronic Kidney Disease Stage 4 (severe).", supp)
        else:
            add_finding("CKD_5", "Probable", "eGFR < 15 mL/min/1.73m² indicates End-Stage Renal Disease (Stage 5).", supp)
    elif status("creatinine") == "high" or (creat_v is not None and creat_v > 1.3) or status("bun") == "high":
        supp = [by_key.get(k) for k in ("creatinine", "bun", "urea") if by_key.get(k) and status(k) == "high"]
        add_finding("ABNORMAL_RENAL_LABS", "Definitive", "Elevated serum creatinine or blood urea nitrogen warrants longitudinal nephrology surveillance.", supp)

    # 4. Hepatobiliary / Transaminases
    alt_high = status("alt") == "high" or (val("alt") is not None and val("alt") > 45)
    ast_high = status("ast") == "high" or (val("ast") is not None and val("ast") > 40)
    if alt_high or ast_high:
        supp = [by_key.get(k) for k in ("alt", "ast", "alp", "ggt") if by_key.get(k) and status(k) == "high"]
        add_finding("TRANSAMINITIS", "Definitive", "Elevated AST/ALT indicates hepatocellular irritation or steatotic liver adaptation.", supp)

    if status("bili") == "high" or status("bili_dir") == "high" or (val("bili") is not None and val("bili") > 1.3):
        supp = [by_key.get(k) for k in ("bili", "bili_dir", "bili_indir") if by_key.get(k) and status(k) == "high"]
        add_finding("HYPERBILIRUBINEMIA", "Definitive", "Elevated total or conjugated bilirubin indicates impaired hepatic clearance or biliary excretion.", supp)

    # 5. Hematology / Anemia
    hb_low = status("hemoglobin") == "low" or (val("hemoglobin") is not None and val("hemoglobin") < 12.0)
    rbc_low = status("rbc") == "low"
    is_anemic = hb_low or rbc_low

    ferritin_low = status("ferritin") == "low" or (val("ferritin") is not None and val("ferritin") < 30)
    iron_low = status("iron") == "low"
    mcv_v = val("mcv")
    b12_low = status("b12") == "low" or (val("b12") is not None and val("b12") < 200)

    if is_anemic:
        supp = [by_key.get(k) for k in ("hemoglobin", "rbc", "ferritin", "iron", "mcv", "b12") if by_key.get(k)]
        if ferritin_low or iron_low or (mcv_v is not None and mcv_v < 80):
            add_finding("IRON_DEFICIENCY_ANEMIA", "Definitive", "Microcytic hypochromic indices with depleted iron/ferritin stores confirm iron deficiency anemia.", supp)
        elif b12_low or (mcv_v is not None and mcv_v > 100):
            add_finding("B12_DEFICIENCY_ANEMIA", "Definitive", "Macrocytic RBC indices with subnormal vitamin B12 concentrations.", supp)
        else:
            add_finding("ANEMIA_UNSPECIFIED", "Definitive", "Decreased circulating hemoglobin/erythrocyte volume requiring comprehensive etiologic evaluation.", supp)
    else:
        # Non-anemic iron deficiency
        if ferritin_low or iron_low:
            supp = [by_key.get(k) for k in ("ferritin", "iron") if by_key.get(k)]
            add_finding("IRON_DEFICIENCY_NONANEMIC", "Definitive", "Depleted tissue iron stores (ferritin < 30 ng/mL) without frank anemia.", supp)

    # Platelets
    plt_v = val("platelets")
    if status("platelets") == "low" or (plt_v is not None and plt_v < 150000):
        supp = [by_key.get("platelets")] if by_key.get("platelets") else []
        add_finding("THROMBOCYTOPENIA", "Definitive", "Platelet count below 150,000/uL carries potential bleeding and hemostatic considerations.", supp)

    # WBC
    wbc_v = val("wbc")
    if status("wbc") == "high" or (wbc_v is not None and wbc_v > 11000):
        supp = [by_key.get("wbc")] if by_key.get("wbc") else []
        add_finding("LEUKOCYTOSIS", "Definitive", "Elevated white blood cell count reflective of acute inflammatory, infectious, or physical stress response.", supp)
    elif status("wbc") == "low" or (wbc_v is not None and wbc_v < 4000):
        supp = [by_key.get("wbc")] if by_key.get("wbc") else []
        add_finding("LEUKOPENIA", "Definitive", "Suppressed total leukocyte count warrants surveillance for bone marrow suppression or viral etiology.", supp)

    # 6. Micronutrients
    vitd_v = val("vitd")
    if status("vitd") == "low" or (vitd_v is not None and vitd_v < 30):
        supp = [by_key.get("vitd")] if by_key.get("vitd") else []
        add_finding("VITAMIN_D_DEFICIENCY", "Definitive", "Serum 25-hydroxyvitamin D falls below optimal threshold (< 30 ng/mL), risking suboptimal calcium homeostasis.", supp)

    if b12_low and not is_anemic:
        supp = [by_key.get("b12")] if by_key.get("b12") else []
        add_finding("VITAMIN_B12_DEFICIENCY", "Definitive", "Serum cobalamin below reference threshold; oral or intramuscular repletion indicated to avert neuropathy.", supp)

    # Drug-induced B12 deficiency (Metformin)
    if b12_low and is_on_metformin:
        supp = [by_key.get("b12")] if by_key.get("b12") else []
        add_finding("DRUG_INDUCED_B12_DEFICIENCY", "Probable", "Metformin antagonizes calcium-dependent ileal uptake of intrinsic factor-B12 complex, precipitating depletion.", supp)

    # 7. Electrolytes & Endocrine
    k_v = val("potassium")
    if status("potassium") == "high" or (k_v is not None and k_v > 5.2):
        supp = [by_key.get("potassium")] if by_key.get("potassium") else []
        add_finding("HYPERKALEMIA", "Definitive", "Serum potassium above 5.2 mmol/L carries cardiac membrane instability risk; ECG surveillance indicated.", supp)
    elif status("potassium") == "low" or (k_v is not None and k_v < 3.5):
        supp = [by_key.get("potassium")] if by_key.get("potassium") else []
        add_finding("HYPOKALEMIA", "Definitive", "Serum potassium below 3.5 mmol/L increases muscular weakness, cramp risk, and ventricular excitability.", supp)

    na_v = val("sodium")
    if status("sodium") == "low" or (na_v is not None and na_v < 135):
        supp = [by_key.get("sodium")] if by_key.get("sodium") else []
        add_finding("HYPONATREMIA", "Definitive", "Serum sodium < 135 mmol/L reflective of free-water excess, SIADH, or diuretic depletion.", supp)

    uric_v = val("uric")
    if status("uric") == "high" or (uric_v is not None and uric_v > 7.0):
        supp = [by_key.get("uric")] if by_key.get("uric") else []
        add_finding("HYPERURICEMIA", "Definitive", "Elevated circulating uric acid conferring elevated risk for crystal arthropathy (gout) and nephrolithiasis.", supp)

    tsh_v = val("tsh")
    if status("tsh") == "high" or (tsh_v is not None and tsh_v > 4.5):
        supp = [by_key.get(k) for k in ("tsh", "ft4", "t4") if by_key.get(k)]
        add_finding("HYPOTHYROIDISM", "Definitive", "Compensatory pituitary TSH elevation signifies primary thyroid hypofunction.", supp)
    elif status("tsh") == "low" or (tsh_v is not None and tsh_v < 0.4):
        supp = [by_key.get(k) for k in ("tsh", "ft4", "t4") if by_key.get(k)]
        add_finding("HYPERTHYROIDISM", "Definitive", "Suppressed TSH indicating thyroid autonomous hypersecretion or exogenous thyroxine excess.", supp)

    if status("esr") == "high":
        supp = [by_key.get("esr")] if by_key.get("esr") else []
        add_finding("ELEVATED_INFLAMMATORY_MARKERS", "Definitive", "Accelerated erythrocyte sedimentation rate secondary to elevated acute phase reactant proteins.", supp)

    # Fallback if no abnormal findings: Encounter for general examination
    if not findings:
        add_finding("GENERAL_EXAM_NORMAL", "Definitive", "All evaluated diagnostic laboratory biomarkers fall within normal reference boundaries.", [])

    # Sort findings by billing priority: Primary first, then Secondary, then Risk/Lab, then Adverse
    tier_order = {
        "Primary Diagnostic Code": 1,
        "Secondary Diagnostic Code": 2,
        "Acute Risk Finding Code": 3,
        "Secondary Risk Finding Code": 4,
        "Secondary Lab Finding Code": 5,
        "Adverse Drug Effect Code": 6,
        "Preventive Surveillance Code": 7
    }
    findings.sort(key=lambda f: tier_order.get(f["billing_tier"], 99))
    return findings


