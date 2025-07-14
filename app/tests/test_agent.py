import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.memory import memory_store
import time

client = TestClient(app)

USER_ID = "testuser"
TIME = "12:00"

@pytest.fixture(autouse=True)
def clear_memory():
    memory_store.clear(USER_ID)
    yield
    memory_store.clear(USER_ID)

def test_health_check():
    """Test the health check endpoint."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "running" in resp.json()["message"].lower()

def test_schedule_exercise():
    """Test scheduling an exercise."""
    resp = client.post("/schedule", json={"user_id": USER_ID, "time": TIME})
    assert resp.status_code == 200
    assert f"Exercise scheduled for {TIME}" in resp.json()["message"]

def test_run_now_and_status():
    """Test running exercise immediately and checking status."""
    # Schedule first
    client.post("/schedule", json={"user_id": USER_ID, "time": TIME})
    
    # Run now
    resp = client.post("/run-now", json={"user_id": USER_ID})
    assert resp.status_code == 200
    assert "exercise" in resp.json()["message"].lower()
    
    # Check status
    status = client.get(f"/status?user_id={USER_ID}")
    assert status.status_code == 200
    data = status.json()
    assert data["user_id"] == USER_ID
    assert data["last_exercise"]
    assert data["reminders_sent"] == 0
    assert data["status"] == "waiting for feedback"

def test_feedback_flow():
    """Test the complete feedback flow."""
    # Send exercise
    client.post("/run-now", json={"user_id": USER_ID})
    
    # Submit feedback
    resp = client.post("/feedback", json={"user_id": USER_ID, "feedback": "Done!"})
    assert resp.status_code == 200
    
    # Check status
    status = client.get(f"/status?user_id={USER_ID}")
    assert status.json()["feedback"] == "Done!"
    assert status.json()["status"] == "completed"

def test_feedback_without_exercise():
    """Test submitting feedback without an exercise."""
    resp = client.post("/feedback", json={"user_id": USER_ID, "feedback": "Done!"})
    assert resp.status_code == 400
    assert "No exercise sent yet" in resp.json()["detail"]

def test_reminders():
    """Test reminder functionality."""
    # Send exercise first
    client.post("/run-now", json={"user_id": USER_ID})
    
    # Simulate reminders by calling run-now multiple times
    for i in range(1, 4):
        resp = client.post("/run-now", json={"user_id": USER_ID})
        assert resp.status_code == 200
        message = resp.json()["message"].lower()
        assert "reminder" in message or "waiting" in message
    
    # After 3 reminders, should indicate maximum reached
    resp = client.post("/run-now", json={"user_id": USER_ID})
    assert resp.status_code == 200
    message = resp.json()["message"].lower()
    assert "waiting" in message or "maximum" in message

def test_delete_schedule():
    """Test deleting a schedule."""
    # Schedule first
    client.post("/schedule", json={"user_id": USER_ID, "time": TIME})
    
    # Delete schedule
    resp = client.delete(f"/schedule?user_id={USER_ID}")
    assert resp.status_code == 200
    assert "cancelled" in resp.json()["message"].lower()

def test_reset_session():
    """Test resetting a user session."""
    # Create some session data
    client.post("/run-now", json={"user_id": USER_ID})
    
    # Reset session
    resp = client.post(f"/reset?user_id={USER_ID}")
    assert resp.status_code == 200
    assert "reset" in resp.json()["message"].lower()
    
    # Verify session is cleared
    try:
        status = client.get(f"/status?user_id={USER_ID}")
        assert status.status_code == 404
    except:
        pass  # Expected if session doesn't exist

def test_status_not_found():
    """Test status endpoint with non-existent user."""
    resp = client.get("/status?user_id=nonexistent")
    assert resp.status_code == 404
    assert "User session not found" in resp.json()["detail"]

def test_multiple_users():
    """Test handling multiple users simultaneously."""
    user1, user2 = "user1", "user2"
    
    try:
        # Send exercises to both users
        client.post("/run-now", json={"user_id": user1})
        client.post("/run-now", json={"user_id": user2})
        
        # Check both have exercises
        status1 = client.get(f"/status?user_id={user1}")
        status2 = client.get(f"/status?user_id={user2}")
        
        assert status1.json()["last_exercise"]
        assert status2.json()["last_exercise"]
        
        # Submit feedback for user1 only
        client.post("/feedback", json={"user_id": user1, "feedback": "Done!"})
        
        # Check statuses
        status1 = client.get(f"/status?user_id={user1}")
        status2 = client.get(f"/status?user_id={user2}")
        
        assert status1.json()["status"] == "completed"
        assert status2.json()["status"] == "waiting for feedback"
        
    finally:
        # Cleanup
        memory_store.clear(user1)
        memory_store.clear(user2)