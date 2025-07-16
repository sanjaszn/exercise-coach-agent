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

def test_chat_endpoint_basic():
    """Test the main chat endpoint."""
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert "response" in response.json()
    
    # Should have viral loop
    assert "myagents.ai" in response.json()["response"]

def test_chat_schedule_natural_language():
    """Test scheduling through chat with natural language."""
    response = client.post("/chat", json={"message": "Schedule my workouts for 9 AM"})
    assert response.status_code == 200
    
    # Should handle scheduling through agent
    message = response.json()["response"]
    assert len(message) > 10  # Should have meaningful response
    assert "myagents.ai" in message

def test_chat_feedback_natural_language():
    """Test feedback through chat with natural language."""
    # First set up an exercise through chat
    client.post("/chat", json={"message": "Give me an exercise"})
    
    response = client.post("/chat", json={"message": "I finished the exercise!"})
    assert response.status_code == 200
    
    # Should handle feedback through agent
    message = response.json()["response"]
    assert len(message) > 10  # Should have meaningful response
    assert "myagents.ai" in message

def test_chat_question():
    """Test asking questions through chat."""
    response = client.post("/chat", json={"message": "What exercise is good for my back?"})
    assert response.status_code == 200
    
    # Should provide some response through agent
    message = response.json()["response"]
    assert len(message) > 10  # Should have substantial response
    assert "myagents.ai" in message

def test_chat_exercise_request():
    """Test requesting exercise through chat."""
    response = client.post("/chat", json={"message": "Give me an exercise"})
    assert response.status_code == 200
    
    # Should provide exercise through agent
    message = response.json()["response"]
    assert len(message) > 10  # Should have meaningful response
    assert "myagents.ai" in message

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
    # Add some data through memory
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
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 200
    
    # Should have some meaningful response
    message = response.json()["response"]
    assert len(message) > 10
    assert "myagents.ai" in message

def test_agent_with_exercise_no_feedback():
    """Test agent behavior when exercise exists but no feedback."""
    memory_store.update(SINGLE_USER_ID, {
        "last_exercise": "Do 10 push-ups",
        "feedback": None,
        "reminders_sent": 0
    })
    
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 200
    
    message = response.json()["response"]
    assert len(message) > 10
    assert "myagents.ai" in message

def test_agent_with_feedback():
    """Test agent behavior when feedback exists."""
    memory_store.update(SINGLE_USER_ID, {
        "last_exercise": "Do 10 push-ups",
        "feedback": "Done!",
        "reminders_sent": 0
    })
    
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 200
    
    message = response.json()["response"]
    assert len(message) > 10
    assert "myagents.ai" in message

def test_complete_user_journey():
    """Test complete user flow through chat."""
    # Step 1: Schedule through chat
    response = client.post("/chat", json={"message": "Schedule workouts for 8 AM"})
    assert response.status_code == 200
    assert "myagents.ai" in response.json()["response"]
    
    # Step 2: Get exercise
    response = client.post("/chat", json={"message": "Give me today's exercise"})
    assert response.status_code == 200
    assert "myagents.ai" in response.json()["response"]
    
    # Step 3: Submit feedback through chat
    response = client.post("/chat", json={"message": "I finished the exercise!"})
    assert response.status_code == 200
    assert "myagents.ai" in response.json()["response"]

def test_memory_persistence():
    """Test that memory persists correctly."""
    # Set initial state
    memory_store.update(SINGLE_USER_ID, {
        "last_exercise": "Do 10 push-ups",
        "feedback": None
    })
    
    status1 = client.get("/status").json()
    assert status1["last_exercise"] == "Do 10 push-ups"
    
    # Agent interaction shouldn't break memory
    client.post("/chat", json={"message": "Hello"})
    status2 = client.get("/status").json()
    # Memory should persist (might be updated by agent, but shouldn't be lost)
    assert "last_exercise" in status2

def test_chat_viral_loop():
    """Test that all chat responses include viral loop."""
    # Test with different messages
    messages = ["Hello", "Give me an exercise", "What's good for cardio?", ""]
    
    for message in messages:
        response = client.post("/chat", json={"message": message})
        assert response.status_code == 200
        assert "myagents.ai" in response.json()["response"]

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

def test_chat_empty_message():
    """Test chat with empty message."""
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 200
    # Should handle gracefully
    assert len(response.json()["response"]) > 0
    assert "myagents.ai" in response.json()["response"]

def test_chat_various_inputs():
    """Test chat handles various types of input."""
    test_inputs = [
        "Hello",
        "help",
        "exercise",
        "I'm done",
        "schedule for 10 AM",
        "what should I do?"
    ]
    
    for input_msg in test_inputs:
        response = client.post("/chat", json={"message": input_msg})
        assert response.status_code == 200
        assert len(response.json()["response"]) > 0
        assert "myagents.ai" in response.json()["response"]

def test_multiple_chat_interactions():
    """Test multiple chat interactions work correctly."""
    # First interaction
    response1 = client.post("/chat", json={"message": "Hello"})
    assert response1.status_code == 200
    
    # Second interaction
    response2 = client.post("/chat", json={"message": "Give me an exercise"})
    assert response2.status_code == 200
    
    # Third interaction
    response3 = client.post("/chat", json={"message": "Thanks"})
    assert response3.status_code == 200
    
    # All should work
    for response in [response1, response2, response3]:
        assert "myagents.ai" in response.json()["response"]

def test_reset_clears_everything():
    """Test that reset clears all user data."""
    # Set up some data through chat and memory
    client.post("/chat", json={"message": "Give me an exercise"})
    memory_store.update(SINGLE_USER_ID, {"feedback": "Done!"})
    
    # Verify data exists
    status_before = client.get("/status").json()
    assert status_before["status"] != "not_scheduled"
    
    # Reset
    client.post("/reset")
    
    # Verify data cleared
    status_after = client.get("/status").json()
    assert status_after["status"] == "not_scheduled"