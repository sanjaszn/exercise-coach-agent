import pytest
from fastapi.testclient import TestClient
from main import app
from memory import memory_store

client = TestClient(app)

USER_ID = "testuser"
TIME = "12:00"

@pytest.fixture(autouse=True)
def clear_memory():
    memory_store.clear(USER_ID)
    yield
    memory_store.clear(USER_ID)

def test_schedule_exercise():
    resp = client.post("/schedule", json={"user_id": USER_ID, "time": TIME})
    assert resp.status_code == 200
    assert f"Exercise scheduled for {TIME}" in resp.json()["message"]

def test_run_now_and_status():
    client.post("/schedule", json={"user_id": USER_ID, "time": TIME})
    resp = client.post("/run-now", json={"user_id": USER_ID})
    assert resp.status_code == 200
    assert "exercise" in resp.json()["message"].lower()
    status = client.get(f"/status?user_id={USER_ID}")
    assert status.status_code == 200
    data = status.json()
    assert data["user_id"] == USER_ID
    assert data["last_exercise"]
    assert data["reminders_sent"] == 0
    assert data["status"] == "waiting for feedback"

def test_feedback_flow():
    client.post("/run-now", json={"user_id": USER_ID})
    resp = client.post("/feedback", json={"user_id": USER_ID, "feedback": "Done!"})
    assert resp.status_code == 200
    assert "thanks for your feedback" in resp.json()["message"].lower()
    status = client.get(f"/status?user_id={USER_ID}")
    assert status.json()["feedback"] == "Done!"
    assert status.json()["status"] == "completed"

def test_reminders():
    client.post("/run-now", json={"user_id": USER_ID})
    # Simulate reminders
    for i in range(1, 4):
        resp = client.post("/run-now", json={"user_id": USER_ID})
        assert f"reminder {i}" in resp.json()["message"].lower() or "waiting for your feedback" in resp.json()["message"].lower()
    # After 3 reminders, should stop
    resp = client.post("/run-now", json={"user_id": USER_ID})
    assert "waiting for your feedback" in resp.json()["message"].lower() or "maximum reminders" in resp.json()["message"].lower()

def test_delete_schedule():
    client.post("/schedule", json={"user_id": USER_ID, "time": TIME})
    resp = client.delete(f"/schedule?user_id={USER_ID}")
    assert resp.status_code == 200
    assert "cancelled" in resp.json()["message"].lower() 