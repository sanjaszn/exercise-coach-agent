import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.memory import memory_store
from app.scheduler import SINGLE_USER_ID
from app.agent import fetch_coach_instructions, parse_coach_prompt, send_exercise_node, send_reminder_node
from datetime import datetime, timedelta
from unittest.mock import patch
import requests  # Added import

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_memory():
    """Clear memory before and after each test."""
    memory_store.clear(SINGLE_USER_ID)
    yield
    memory_store.clear(SINGLE_USER_ID)

@pytest.fixture
def mock_coach_api():
    """Mock the coach commands API response."""
    with patch("requests.get") as mock_get:
        yield mock_get

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

def test_fetch_coach_instructions(mock_coach_api):
    """Test fetching coach instructions with API and fallback."""
    # Mock successful API response
    mock_coach_api.return_value.status_code = 200
    mock_coach_api.return_value.json.return_value = {
        "instruction_id": "123",
        "coach_id": "coach_001",
        "user_id": SINGLE_USER_ID,
        "prompt": "Remind the user about their weight loss goal.",
        "timestamp": "2025-07-16T10:00:00Z"
    }
    
    # Test fetching new instruction
    instruction = fetch_coach_instructions(SINGLE_USER_ID, "coach_001")
    assert instruction["prompt"] == "Remind the user about their weight loss goal."
    assert memory_store.get(SINGLE_USER_ID)["coach_instruction"] == instruction
    
    # Test caching (no API call if within 1 hour)
    mock_coach_api.reset_mock()
    instruction = fetch_coach_instructions(SINGLE_USER_ID, "coach_001")
    assert instruction["prompt"] == "Remind the user about their weight loss goal."
    mock_coach_api.assert_not_called()
    
    # Test API failure fallback
    mock_coach_api.return_value.raise_for_status.side_effect = requests.RequestException
    memory_store.update(SINGLE_USER_ID, {
        "coach_instruction": {"prompt": "Cached prompt"},
        "last_instruction_fetch": (datetime.now() - timedelta(hours=2)).isoformat()
    })
    instruction = fetch_coach_instructions(SINGLE_USER_ID, "coach_001")
    assert instruction["prompt"] == "Cached prompt"

def test_parse_coach_prompt():
    """Test parsing different coach prompts."""
    # Goal reminder prompt
    result = parse_coach_prompt("Remind the user about their goals")
    assert result["motivation_type"] == "goal_reminder"
    assert result["include_goals"] is True
    assert result["warning_tone"] is False
    
    # Warning prompt
    result = parse_coach_prompt("Warn about lack of exercise")
    assert result["motivation_type"] == "warning"
    assert result["include_goals"] is False
    assert result["warning_tone"] is True
    
    # Default prompt
    result = parse_coach_prompt("Stay motivated!")
    assert result["motivation_type"] == "general"
    assert result["include_goals"] is False
    assert result["warning_tone"] is False

def test_send_exercise_node_with_coach_instructions(mock_coach_api):
    """Test send_exercise_node with coach instructions."""
    # Set up user context
    memory_store.update(SINGLE_USER_ID, {
        "goals": "Lose 10 pounds",
        "last_exercise": None,
        "reminders_sent": 0
    })
    
    # Mock coach instruction
    mock_coach_api.return_value.status_code = 200
    mock_coach_api.return_value.json.return_value = {
        "instruction_id": "123",
        "coach_id": "coach_001",
        "user_id": SINGLE_USER_ID,
        "prompt": "Remind the user their weight loss goal and warn about consistency.",
        "timestamp": "2025-07-16T10:00:00Z"
    }
    
    # Run node
    state = {
        "input": "",
        "user_id": SINGLE_USER_ID,
        "coach_id": "coach_001",
        "node_output": "",
        "output": ""
    }
    result = send_exercise_node(state)
    
    # Verify customized message
    message = result["node_output"].lower()
    assert "do 10 push-ups" in message
    assert "lose 10 pounds" in message
    assert "stay consistent" in message

def test_send_reminder_node_with_coach_instructions(mock_coach_api):
    """Test send_reminder_node with coach instructions."""
    # Set up user context with inactivity
    memory_store.update(SINGLE_USER_ID, {
        "goals": "Run a marathon",
        "last_exercise": "Do 10 push-ups",
        "last_exercise_date": (datetime.now().date() - timedelta(days=4)).isoformat(),
        "feedback": None,
        "reminders_sent": 0
    })
    
    # Mock coach instruction
    mock_coach_api.return_value.status_code = 200
    mock_coach_api.return_value.json.return_value = {
        "instruction_id": "123",
        "coach_id": "coach_001",
        "user_id": SINGLE_USER_ID,
        "prompt": "Warn about lack of exercise and remind about goals.",
        "timestamp": "2025-07-16T10:00:00Z"
    }
    
    # Run node
    state = {
        "input": "",
        "user_id": SINGLE_USER_ID,
        "coach_id": "coach_001",
        "node_output": "",
        "output": ""
    }
    result = send_reminder_node(state)
    
    # Verify customized reminder
    message = result["node_output"].lower()
    assert "reminder" in message
    assert "run a marathon" in message
    assert "3 days" in message

def test_route_to_node_with_warning(mock_coach_api):
    """Test route_to_node prioritizes reminders for inactivity with warning prompt."""
    # Set up user context with inactivity
    memory_store.update(SINGLE_USER_ID, {
        "last_exercise": "Do 10 push-ups",
        "last_exercise_date": (datetime.now().date() - timedelta(days=4)).isoformat(),
        "feedback": None,
        "reminders_sent": 0
    })
    
    # Mock coach instruction
    mock_coach_api.return_value.status_code = 200
    mock_coach_api.return_value.json.return_value = {
        "instruction_id": "123",
        "coach_id": "coach_001",
        "user_id": SINGLE_USER_ID,
        "prompt": "Warn about lack of exercise.",
        "timestamp": "2025-07-16T10:00:00Z"
    }
    
    # Run routing
    from app.agent import route_to_node
    state = {
        "input": "",
        "user_id": SINGLE_USER_ID,
        "coach_id": "coach_001",
        "node_output": "",
        "output": ""
    }
    result = route_to_node(state)
    assert result == "send_reminder"