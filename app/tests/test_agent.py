# app/tests/test_agent.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.memory import memory_store
from app.scheduler import SINGLE_USER_ID

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_memory():
    """Clear memory before and after each test."""
    memory_store.clear(SINGLE_USER_ID)
    yield
    memory_store.clear(SINGLE_USER_ID)

def test_health_check():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "exercise coach" in response.json()["message"].lower()

def test_schedule_endpoint():
    """Test scheduling exercise time."""
    response = client.post("/schedule?time=09:00")
    assert response.status_code == 200
    assert "09:00" in response.json()["message"]
    
    # Verify it's stored in memory
    status = client.get("/status").json()
    assert status["scheduled_time"] == "09:00"

def test_feedback_endpoint():
    """Test submitting feedback."""
    # First set up an exercise
    memory_store.update(SINGLE_USER_ID, {"last_exercise": "Do 10 push-ups"})
    
    response = client.post("/feedback?feedback=Completed!")
    assert response.status_code == 200
    assert "feedback received" in response.json()["message"].lower()
    
    # Verify feedback stored
    status = client.get("/status").json()
    assert status["feedback"] == "Completed!"

def test_status_endpoint_no_data():
    """Test status when no data exists."""
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "not_scheduled"

def test_status_endpoint_with_data():
    """Test status with exercise data."""
    memory_store.update(SINGLE_USER_ID, {
        "scheduled_time": "10:00",
        "last_exercise": "Do 10 push-ups",
        "feedback": None,
        "reminders_sent": 0
    })
    
    response = client.get("/status")
    data = response.json()
    assert data["status"] == "waiting_feedback"
    assert data["last_exercise"] == "Do 10 push-ups"
    assert data["scheduled_time"] == "10:00"
    assert data["reminders_sent"] == 0

def test_reset_endpoint():
    """Test resetting user session."""
    # Add some data
    memory_store.update(SINGLE_USER_ID, {
        "last_exercise": "Do 10 push-ups",
        "feedback": "Done"
    })
    
    response = client.post("/reset")
    assert response.status_code == 200
    assert "reset" in response.json()["message"].lower()
    
    # Verify data cleared
    status = client.get("/status").json()
    assert status["status"] == "not_scheduled"

def test_agent_sends_exercise():
    """Test agent sends exercise when none exists."""
    response = client.post("/test-now")
    assert response.status_code == 200
    
    # Agent should either send exercise or check feedback
    message = response.json()["message"].lower()
    has_exercise = "do 10 push-ups" in message
    is_waiting = "waiting" in message
    
    # Either behavior is valid based on routing
    assert has_exercise or is_waiting
    
    # Verify viral loop present
    assert "myagents.ai" in response.json()["message"]

def test_agent_with_exercise_no_feedback():
    """Test agent behavior when exercise exists but no feedback."""
    memory_store.update(SINGLE_USER_ID, {
        "last_exercise": "Do 10 push-ups",
        "feedback": None,
        "reminders_sent": 0
    })
    
    response = client.post("/test-now")
    assert response.status_code == 200
    
    message = response.json()["message"].lower()
    # Should remind or wait for feedback
    assert "reminder" in message or "waiting" in message

def test_agent_with_feedback():
    """Test agent behavior when feedback exists."""
    memory_store.update(SINGLE_USER_ID, {
        "last_exercise": "Do 10 push-ups",
        "feedback": "Done!",
        "reminders_sent": 0
    })
    
    response = client.post("/test-now")
    assert response.status_code == 200
    
    message = response.json()["message"].lower()
    # Should thank user or acknowledge feedback
    assert "thanks" in message or "feedback" in message or "done!" in message

def test_complete_user_journey():
    """Test complete user flow."""
    # Step 1: Schedule
    client.post("/schedule?time=08:00")
    status = client.get("/status").json()
    assert status["status"] == "scheduled"
    
    # Step 2: Manually add exercise (since time-based won't trigger)
    memory_store.update(SINGLE_USER_ID, {
        "scheduled_time": "08:00",
        "last_exercise": "Do 10 push-ups",
        "feedback": None,
        "reminders_sent": 0
    })
    
    status = client.get("/status").json()
    assert status["status"] == "waiting_feedback"
    
    # Step 3: Submit feedback
    client.post("/feedback?feedback=Finished!")
    status = client.get("/status").json()
    assert status["status"] == "completed"
    assert status["feedback"] == "Finished!"
    
    # Step 4: Agent should acknowledge
    response = client.post("/test-now")
    message = response.json()["message"].lower()
    assert "thanks" in message or "feedback" in message or "finished!" in message

def test_memory_persistence():
    """Test that memory persists correctly."""
    # Set initial state
    memory_store.update(SINGLE_USER_ID, {
        "last_exercise": "Do 10 push-ups",
        "feedback": None
    })
    
    status1 = client.get("/status").json()
    assert status1["last_exercise"] == "Do 10 push-ups"
    
    # Agent shouldn't change exercise
    client.post("/test-now")
    status2 = client.get("/status").json()
    assert status2["last_exercise"] == "Do 10 push-ups"
    
    # Add feedback
    client.post("/feedback?feedback=Great!")
    status3 = client.get("/status").json()
    assert status3["last_exercise"] == "Do 10 push-ups"  # Same exercise
    assert status3["feedback"] == "Great!"  # New feedback

def test_multiple_schedule_updates():
    """Test updating schedule multiple times."""
    # Schedule 1
    client.post("/schedule?time=07:00")
    assert client.get("/status").json()["scheduled_time"] == "07:00"
    
    # Schedule 2 (should overwrite)
    client.post("/schedule?time=19:30")
    assert client.get("/status").json()["scheduled_time"] == "19:30"

def test_feedback_without_exercise():
    """Test submitting feedback when no exercise exists."""
    # This might fail based on implementation
    response = client.post("/feedback?feedback=No exercise!")
    # Should handle gracefully
    assert response.status_code in [200, 400]  # Either is acceptable

def test_agent_viral_loop():
    """Test that all agent responses include viral loop."""
    # Test with different states
    responses = []
    
    # Empty state
    responses.append(client.post("/test-now"))
    
    # With exercise
    memory_store.update(SINGLE_USER_ID, {"last_exercise": "Do 10 push-ups"})
    responses.append(client.post("/test-now"))
    
    # With feedback
    memory_store.update(SINGLE_USER_ID, {"feedback": "Done"})
    responses.append(client.post("/test-now"))
    
    # All should have viral loop
    for response in responses:
        assert "myagents.ai" in response.json()["message"]

def test_deterministic_exercise():
    """Test that exercise function is deterministic."""
    from app.tools import send_exercise_fn
    
    # Should always return same exercise
    exercise1 = send_exercise_fn(SINGLE_USER_ID)
    memory_store.clear(SINGLE_USER_ID)
    exercise2 = send_exercise_fn(SINGLE_USER_ID)
    
    assert exercise1 == exercise2 == "Do 10 push-ups"

def test_status_response_format():
    """Test that status response has correct format."""
    memory_store.update(SINGLE_USER_ID, {
        "scheduled_time": "09:00",
        "last_exercise": "Do 10 push-ups",
        "feedback": "Done",
        "reminders_sent": 2
    })
    
    response = client.get("/status")
    data = response.json()
    
    # Check all expected fields
    assert "status" in data
    assert "scheduled_time" in data
    assert "last_exercise" in data
    assert "feedback" in data
    assert "reminders_sent" in data
    
    assert data["scheduled_time"] == "09:00"
    assert data["last_exercise"] == "Do 10 push-ups"
    assert data["feedback"] == "Done"
    assert data["reminders_sent"] == 2
    assert data["status"] == "completed"