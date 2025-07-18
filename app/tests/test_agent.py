import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.memory import memory_store
from app.scheduler import SINGLE_USER_ID
from datetime import datetime, timedelta

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

@pytest.mark.timeout(120)
def test_chat_endpoint():
    """Test the main chat endpoint."""
    response = client.post("/chat", json={"message": "Hello"})
    assert response.status_code == 200
    assert "response" in response.json()
    assert "myagents.ai" in response.json()["response"]

def test_status_endpoint():
    """Test status endpoint."""
    response = client.get("/status")
    assert response.status_code == 200
    assert "status" in response.json()

def test_reset_endpoint():
    """Test reset endpoint."""
    response = client.post("/reset")
    assert response.status_code == 200
    assert "reset" in response.json()["message"].lower()

def test_coach_commands_endpoint():
    """Test coach commands endpoint."""
    response = client.get("/coach-commands?user_id=test_user&coach_id=test_coach")
    assert response.status_code == 200
    assert "prompt" in response.json()

def test_coach_chat_endpoint():
    """Test coach chat endpoint."""
    response = client.post("/coach/chat", json={
        "user_id": "test_user",
        "prompt": "Test instruction"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "instruction sent"

def test_memory_works():
    """Test ChromaDB memory works."""
    memory_store.set("test_user", {"test": "data"})
    result = memory_store.get("test_user")
    assert result["test"] == "data"
    
    memory_store.update("test_user", {"new": "value"})
    result = memory_store.get("test_user")
    assert result["test"] == "data"
    assert result["new"] == "value"
    
    memory_store.clear("test_user")
    result = memory_store.get("test_user")
    assert result == {}

def test_schedule_workout_via_chat():
    """Test user can schedule workout via chat."""
    current_time = datetime.now()
    time_str = f"{current_time.hour:02d}:{current_time.minute:02d}"
    response = client.post("/chat", json={"message": f"Schedule my workout for {time_str}"})
    assert response.status_code == 200
    assert time_str in response.json()["response"]  # Check if scheduled time is in response
    assert "myagents.ai" in response.json()["response"]
    # Verify stored schedule
    session = memory_store.get(SINGLE_USER_ID)
    assert session.get("scheduled_time") == time_str

def test_reminder_logic():
    """Test reminder logic works."""
    from app.tools import should_send_exercise, should_send_reminder
    
    # Test should_send_exercise at scheduled time
    current_time = datetime.now()
    memory_store.update(SINGLE_USER_ID, {
        "scheduled_hour": current_time.hour,
        "scheduled_minute": current_time.minute,
        "last_exercise_date": (current_time.date() - timedelta(days=1)).isoformat()
    })
    
    assert should_send_exercise(SINGLE_USER_ID) == True
    
    # Test should_send_reminder when exercise sent hours ago
    memory_store.update(SINGLE_USER_ID, {
        "last_exercise": "Do 10 push-ups",
        "feedback": None,
        "reminders_sent": 0,
        "exercise_sent_at": (current_time - timedelta(hours=3)).isoformat()
    })
    
    assert should_send_reminder(SINGLE_USER_ID) == True

def test_chromadb_connection():
    """Test ChromaDB connection with prints."""
    print("\n=== Testing ChromaDB Connection ===")
    
    # Test basic operations
    print("1. Testing set operation...")
    memory_store.set("test_connection", {"test": "chromadb_works"})
    
    print("2. Testing get operation...")
    result = memory_store.get("test_connection")
    print(f"Retrieved: {result}")
    
    print("3. Testing update operation...")
    memory_store.update("test_connection", {"updated": True})
    result = memory_store.get("test_connection")
    print(f"After update: {result}")
    
    print("4. Testing clear operation...")
    memory_store.clear("test_connection")
    result = memory_store.get("test_connection")
    print(f"After clear: {result}")
    
    assert result == {}
    print("=== ChromaDB Connection Test PASSED ===")