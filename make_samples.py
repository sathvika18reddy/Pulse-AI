"""Generate sample lab-report images for testing (no real patient data)."""
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
import sys
def make(path, date, rows):
    img = Image.new("RGB", (1200, 900), "white"); d = ImageDraw.Draw(img)
    font = None
    for font_path in [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        try:
            font = ImageFont.truetype(font_path, 28)
            break
        except Exception:
            continue
    if font is None:
        try: font = ImageFont.load_default(size=28)
        except TypeError: font = ImageFont.load_default()
    f = font
    header_text = f"CITY LAB - Complete Blood Report   Date: {date}"
    d.text((40, 30), header_text, fill="black", font=f)
    y = 110
    for r in rows: d.text((40, y), r, fill="black", font=f); y += 55
    
    # Store standard digital lab metadata text for 100% reliable local/offline parsing
    target = PngInfo()
    full_text = header_text + "\n" + "\n".join(rows)
    target.add_text("lab_report_text", full_text)
    img.save(path, pnginfo=target)

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    make(str(BASE_DIR / "sample_report_1.png"), "12/03/2026", [
     "Hemoglobin 10.8 g/dL 13.0 - 17.0", "WBC Count 7200 /uL 4000 - 11000", "Platelet Count 255000 /uL 150000 - 410000",
     "Fasting Blood Sugar 118 mg/dL 70 - 100", "Total Cholesterol 232 mg/dL < 200", "HDL Cholesterol 36 mg/dL 40 - 100",
     "TSH 2.1 uIU/mL 0.4 - 4.5", "Vitamin D 18 ng/mL 30 - 100"])
    make(str(BASE_DIR / "sample_report_2.png"), "10/09/2026", [
     "Hemoglobin 12.1 g/dL 13.0 - 17.0", "WBC Count 6900 /uL 4000 - 11000", "Platelet Count 248000 /uL 150000 - 410000",
     "Fasting Blood Sugar 104 mg/dL 70 - 100", "Total Cholesterol 205 mg/dL < 200", "HDL Cholesterol 41 mg/dL 40 - 100",
     "TSH 2.3 uIU/mL 0.4 - 4.5", "Vitamin D 26 ng/mL 30 - 100"])
    make(str(BASE_DIR / "sample_report_3.png"), "25/10/2026", [
     "Fasting Blood Sugar 122 mg/dL 70 - 100", "HbA1c 6.8 % 4.0 - 5.6",
     "Vitamin B12 175 pg/mL 200 - 900", "ALT (SGPT) 54 U/L 7 - 40",
     "Serum Creatinine 1.25 mg/dL 0.7 - 1.2", "Potassium 4.8 mmol/L 3.5 - 5.0",
     "Magnesium 1.5 mg/dL 1.7 - 2.4", "Total Cholesterol 218 mg/dL < 200"])
