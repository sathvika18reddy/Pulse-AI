import io, os
from pathlib import Path
import pytest
from PIL import Image
import app

SAMPLE_IMG = Path(__file__).resolve().parent.parent / "sample_report_1.png"

@pytest.fixture
def client():
    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        yield client

def test_upload_rejects_non_image_or_pdf(client):
    # Text file
    res = client.post("/api/upload", data={"file": (io.BytesIO(b"Hello world"), "notes.txt")})
    assert res.status_code == 400
    assert "Upload a PDF or image" in res.get_json()["error"]

    # Executable file
    res_exe = client.post("/api/upload", data={"file": (io.BytesIO(b"binary"), "malware.exe")})
    assert res_exe.status_code == 400
    assert "Upload a PDF or image" in res_exe.get_json()["error"]

    # No file uploaded
    res_none = client.post("/api/upload", data={})
    assert res_none.status_code == 400
    assert "No file uploaded" in res_none.get_json()["error"]

def test_upload_unreadable_blank_image(client):
    # Blank white image with no text should return HTTP 422
    img = Image.new("RGB", (400, 200), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    res = client.post("/api/upload", data={"file": (buf, "blank.png")})
    assert res.status_code == 422
    assert "Couldn't find any known lab values" in res.get_json()["error"]

def test_upload_valid_sample_report(client):
    with open(SAMPLE_IMG, "rb") as f:
        res = client.post("/api/upload", data={"file": f, "lang": "en"})
    assert res.status_code == 200
    data = res.get_json()
    assert "id" in data
    assert len(data["results"]) >= 6
    assert "summary" in data

def test_summary_and_chat_404_for_unknown_id(client):
    res_sum = client.post("/api/summary/nonexistent_id", json={"lang": "en"})
    assert res_sum.status_code == 404
    assert res_sum.get_json()["error"] == "Report not found"

    res_chat = client.post("/api/chat/nonexistent_id", json={"question": "hello", "lang": "en"})
    assert res_chat.status_code == 404
    assert res_chat.get_json()["error"] == "Report not found"

def test_trends_endpoint(client):
    res = client.get("/api/trends")
    assert res.status_code == 200
    trends = res.get_json()
    assert isinstance(trends, dict)

def test_reports_listing_fetch_export_and_delete(client):
    sess = "test_user_session_99"
    with open(SAMPLE_IMG, "rb") as f:
        up = client.post("/api/upload", data={"file": f, "session_id": sess, "sex": "male", "age": "45"})
    assert up.status_code == 200
    rid = up.get_json()["id"]

    # 1. Listing reports
    list_res = client.get(f"/api/reports?session_id={sess}")
    assert list_res.status_code == 200
    reports = list_res.get_json()
    assert any(r["id"] == rid for r in reports)

    # 2. Fetch specific report
    get_res = client.get(f"/api/report/{rid}?session_id={sess}")
    assert get_res.status_code == 200
    assert get_res.get_json()["patient_sex"] == "male"
    assert get_res.get_json()["patient_age"] == 45

    # 3. Export printable report
    exp_res = client.get(f"/api/export/{rid}?session_id={sess}")
    assert exp_res.status_code == 200
    assert b"PULSE AI" in exp_res.data
    assert b"Print or Save as PDF" in exp_res.data

    # 4. Delete report
    del_res = client.delete(f"/api/report/{rid}?session_id={sess}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # 5. Verify deleted
    verify_res = client.get(f"/api/report/{rid}?session_id={sess}")
    assert verify_res.status_code == 404

def test_confirm_report_endpoint(client):
    with open(SAMPLE_IMG, "rb") as f:
        up = client.post("/api/upload", data={"file": f})
    assert up.status_code == 200
    rec = up.get_json()
    rid = rec["id"]
    
    # Modify a value: set hemoglobin to 15.0 (normal)
    modified_rows = [dict(r) for r in rec["results"]]
    for r in modified_rows:
        if r["key"] == "hemoglobin":
            r["value"] = 15.0
            
    conf_res = client.post(f"/api/confirm/{rid}", json={"results": modified_rows, "sex": "male"})
    assert conf_res.status_code == 200
    updated = conf_res.get_json()
    hb = next(r for r in updated["results"] if r["key"] == "hemoglobin")
    assert hb["value"] == 15.0
    assert hb["status"] == "normal"
    assert "summary" in updated
    assert "speech_script" in updated

def test_streaming_chat_endpoint(client):
    with open(SAMPLE_IMG, "rb") as f:
        up = client.post("/api/upload", data={"file": f})
    assert up.status_code == 200
    rid = up.get_json()["id"]

    stream_res = client.post(f"/api/chat/{rid}/stream", json={"question": "What is abnormal in my blood report?"})
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.content_type
    
    data = stream_res.data.decode("utf-8")
    assert "data: " in data
    assert "token" in data
    assert "done" in data
    assert "suggestions" in data

def test_speech_script_returned_in_upload_and_summary(client):
    with open(SAMPLE_IMG, "rb") as f:
        up = client.post("/api/upload", data={"file": f})
    assert up.status_code == 200
    data = up.get_json()
    assert "speech_script" in data
    assert len(data["speech_script"]) > 20

    sum_res = client.post(f"/api/summary/{data['id']}", json={"lang": "en"})
    assert sum_res.status_code == 200
    sum_data = sum_res.get_json()
    assert "speech_script" in sum_data

