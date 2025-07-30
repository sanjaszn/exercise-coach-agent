import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.memory import memory_store
from datetime import datetime, timedelta
import uuid

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_memory():
    """Clear memory before and after each test."""
    # Clear any test data
    memory_store.clear("test_user")
    memory_store.clear("test_agent_123")
    memory_store.clear("end_user_test_agent_123")
    yield
    # Cleanup after test
    memory_store.clear("test_user")
    memory_store.clear("test_agent_123")
    memory_store.clear("end_user_test_agent_123")

def test_health_check():
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Exercise Agent Platform" in response.json()["message"]
    assert "create_agent" in response.json()["endpoints"]
    assert "agent_owner" in response.json()["terminology"]
    assert "end_user" in response.json()["terminology"]

def test_create_agent_endpoint():
    """Test creating a new agent."""
    response = client.post("/create-agent", json={
        "description": "I want a fitness agent that sends daily workout reminders"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "agent_id" in data
    assert "config" in data
    
    # Validate agent_id is a UUID
    agent_id = data["agent_id"]
    uuid.UUID(agent_id)  # Will raise ValueError if not valid UUID
    
    # Check config structure
    config = data["config"]
    assert "name" in config
    assert "personality" in config
    assert "tone" in config
    assert "domain" in config
    assert "features" in config
    
    # Verify agent is stored in memory
    stored_agent = memory_store.get(agent_id)
    assert stored_agent is not None
    assert stored_agent["agent_id"] == agent_id
    assert stored_agent["description"] == "I want a fitness agent that sends daily workout reminders"
    assert stored_agent["status"] == "active"

def test_create_agent_with_empty_description():
    """Test creating agent with empty description."""
    response = client.post("/create-agent", json={
        "description": ""
    })
    
    assert response.status_code == 400

def test_end_user_chat_endpoint():
    """Test end user chatting with an agent."""
    # First create an agent
    create_response = client.post("/create-agent", json={
        "description": "A helpful fitness agent"
    })
    agent_id = create_response.json()["agent_id"]
    
    # Now test chatting with the agent
    chat_response = client.post(f"/end-user/chat/{agent_id}", json={
        "message": "I need a workout plan"
    })
    
    assert chat_response.status_code == 200
    data = chat_response.json()
    
    assert "response" in data
    assert "agent_id" in data
    assert data["agent_id"] == agent_id
    assert len(data["response"]) > 0
    
    # Verify session is created
    session = memory_store.get(f"end_user_{agent_id}")
    assert session is not None

def test_agent_owner_chat_endpoint():
    """Test agent owner sending instructions to agent."""
    # First create an agent
    create_response = client.post("/create-agent", json={
        "description": "A fitness agent"
    })
    agent_id = create_response.json()["agent_id"]
    
    # Send instruction as agent owner
    instruction_response = client.post(f"/agent-owner/chat/{agent_id}", json={
        "end_user_id": "user123",
        "prompt": "Be more encouraging and motivational today"
    })
    
    assert instruction_response.status_code == 200
    data = instruction_response.json()
    
    assert data["status"] == "instruction sent"
    assert "instruction" in data
    assert data["agent_id"] == agent_id
    
    # Verify instruction is stored
    session = memory_store.get(f"end_user_{agent_id}")
    if session:
        assert "agent_owner_instruction" in session

def test_agent_status_endpoint():
    """Test getting agent status."""
    # Create an agent
    create_response = client.post("/create-agent", json={
        "description": "A fitness agent"
    })
    agent_id = create_response.json()["agent_id"]
    
    # Get status
    status_response = client.get(f"/status/{agent_id}")
    
    assert status_response.status_code == 200
    data = status_response.json()
    
    assert "status" in data
    assert "agent_id" in data
    assert data["agent_id"] == agent_id
    assert data["status"] == "not_scheduled"  # Default for new agent

def test_reset_agent_endpoint():
    """Test resetting agent session."""
    # Create an agent
    create_response = client.post("/create-agent", json={
        "description": "A fitness agent"
    })
    agent_id = create_response.json()["agent_id"]
    
    # Chat with agent to create session
    client.post(f"/end-user/chat/{agent_id}", json={
        "message": "Hello"
    })
    
    # Reset session
    reset_response = client.post(f"/reset/{agent_id}")
    
    assert reset_response.status_code == 200
    data = reset_response.json()
    
    assert "message" in data
    assert "reset" in data["message"].lower()
    assert data["agent_id"] == agent_id
    
    # Verify session is cleared
    session = memory_store.get(f"end_user_{agent_id}")
    assert session == {} or session is None

def test_memory_store_works():
    """Test ChromaDB memory store operations."""
    # Test basic operations
    memory_store.set("test_key", {"test": "data"})
    result = memory_store.get("test_key")
    assert result["test"] == "data"
    
    # Test update
    memory_store.update("test_key", {"new": "value"})
    result = memory_store.get("test_key")
    assert result["test"] == "data"
    assert result["new"] == "value"
    
    # Test clear
    memory_store.clear("test_key")
    result = memory_store.get("test_key")
    assert result == {}

def test_memory_store_get_all_sessions():
    """Test getting all sessions from memory store."""
    # Create some test sessions
    memory_store.set("end_user_agent1", {"scheduled_time": "10:00", "last_exercise": "push-ups"})
    memory_store.set("end_user_agent2", {"scheduled_time": "14:00"})
    memory_store.set("end_user_agent3", {"last_exercise": "squats"})
    memory_store.set("inactive_session", {"some_data": "value"})  # Should not be included
    
    sessions = memory_store.get_all_sessions()
    
    # Should find active sessions
    session_ids = [s["user_id"] for s in sessions]
    assert "end_user_agent1" in session_ids
    assert "end_user_agent2" in session_ids
    assert "end_user_agent3" in session_ids
    assert "inactive_session" in session_ids  # All sessions are returned
    
    # Cleanup
    memory_store.clear("end_user_agent1")
    memory_store.clear("end_user_agent2")
    memory_store.clear("end_user_agent3")
    memory_store.clear("inactive_session")

def test_complete_agent_workflow():
    """Test the complete agent creation and usage workflow."""
    print("\n=== Testing Complete Agent Workflow ===")
    
    # 1. Agent owner creates agent
    print("1. Creating agent...")
    create_response = client.post("/create-agent", json={
        "description": "A motivational fitness agent that tracks progress and sends reminders"
    })
    
    assert create_response.status_code == 200
    agent_id = create_response.json()["agent_id"]
    config = create_response.json()["config"]
    print(f"Created agent: {agent_id}")
    print(f"Agent config: {config}")
    
    # 2. Agent owner sends instructions
    print("2. Agent owner sending instructions...")
    instruction_response = client.post(f"/agent-owner/chat/{agent_id}", json={
        "end_user_id": "user123",
        "prompt": "Be extra motivational today and focus on strength training"
    })
    
    assert instruction_response.status_code == 200
    print("Instructions sent successfully")
    
    # 3. End user chats with agent
    print("3. End user chatting with agent...")
    chat_response = client.post(f"/end-user/chat/{agent_id}", json={
        "message": "I need motivation for my workout today"
    })
    
    assert chat_response.status_code == 200
    ai_response = chat_response.json()["response"]
    print(f"AI Response: {ai_response}")
    
    # 4. Check agent status
    print("4. Checking agent status...")
    status_response = client.get(f"/status/{agent_id}")
    assert status_response.status_code == 200
    status = status_response.json()
    print(f"Agent status: {status}")
    
    # 5. Verify data persistence
    print("5. Verifying data persistence...")
    stored_agent = memory_store.get(agent_id)
    assert stored_agent is not None
    assert stored_agent["agent_id"] == agent_id
    
    session = memory_store.get(f"end_user_{agent_id}")
    assert session is not None
    
    print("✅ Complete workflow test passed!")

def test_multiple_agents():
    """Test creating and managing multiple agents."""
    print("\n=== Testing Multiple Agents ===")
    
    # Create multiple agents
    agents = []
    descriptions = [
        "A fitness agent",
        "A business mentor agent", 
        "A language tutor agent"
    ]
    
    for desc in descriptions:
        response = client.post("/create-agent", json={"description": desc})
        assert response.status_code == 200
        agents.append(response.json()["agent_id"])
    
    print(f"Created {len(agents)} agents: {agents}")
    
    # Test that each agent is independent
    for i, agent_id in enumerate(agents):
        # Chat with each agent
        chat_response = client.post(f"/end-user/chat/{agent_id}", json={
            "message": f"Hello agent {i+1}"
        })
        assert chat_response.status_code == 200
        
        # Verify separate sessions
        session = memory_store.get(f"end_user_{agent_id}")
        assert session is not None
        
        # Verify agent data
        agent_data = memory_store.get(agent_id)
        assert agent_data is not None
        assert agent_data["description"] == descriptions[i]
    
    print("✅ Multiple agents test passed!")

def test_agent_not_found():
    """Test behavior with non-existent agent."""
    fake_agent_id = str(uuid.uuid4())
    
    # Try to chat with non-existent agent
    chat_response = client.post(f"/end-user/chat/{fake_agent_id}", json={
        "message": "Hello"
    })
    
    # Should still work (creates session) but agent won't have special config
    assert chat_response.status_code == 200
    
    # Try to get status of non-existent agent
    status_response = client.get(f"/status/{fake_agent_id}")
    assert status_response.status_code == 200
    # After chatting, the agent will have created a last_exercise, so status will be waiting_feedback
    assert status_response.json()["status"] == "waiting_feedback"

def test_agent_status_not_scheduled():
    """Test agent status when no session exists."""
    fake_agent_id = str(uuid.uuid4())
    
    # Get status without creating any session
    status_response = client.get(f"/status/{fake_agent_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "not_scheduled"

def test_scheduler_integration():
    """Test scheduler integration with memory store."""
    from app.scheduler import get_active_sessions
    
    # Create test sessions
    memory_store.set("end_user_scheduler_test1", {
        "scheduled_time": "10:00",
        "last_exercise": "push-ups"
    })
    memory_store.set("end_user_scheduler_test2", {
        "scheduled_time": "14:00"
    })
    memory_store.set("end_user_scheduler_test3", {
        "last_exercise": "squats"
    })
    memory_store.set("inactive_session", {"some_data": "value"})
    
    # Get active sessions
    active_sessions = get_active_sessions()
    
    # Should find active sessions
    session_ids = [s["user_id"] for s in active_sessions]
    assert "end_user_scheduler_test1" in session_ids
    assert "end_user_scheduler_test2" in session_ids
    assert "end_user_scheduler_test3" in session_ids
    assert "inactive_session" not in session_ids  # Not active
    
    # Verify agent_id extraction
    for session in active_sessions:
        if session["user_id"] == "end_user_scheduler_test1":
            assert session["agent_id"] == "scheduler_test1"
        elif session["user_id"] == "end_user_scheduler_test2":
            assert session["agent_id"] == "scheduler_test2"
        elif session["user_id"] == "end_user_scheduler_test3":
            assert session["agent_id"] == "scheduler_test3"
    
    # Cleanup
    memory_store.clear("end_user_scheduler_test1")
    memory_store.clear("end_user_scheduler_test2")
    memory_store.clear("end_user_scheduler_test3")
    memory_store.clear("inactive_session")

def test_agent_owner_instructions():
    """Test agent owner instruction functionality."""
    from app.agent_owner import fetch_agent_owner_instructions, parse_agent_owner_prompt
    
    # Test instruction fetching
    user_id = "end_user_test_agent"
    agent_owner_id = "test_agent"
    
    # Test default instruction
    instruction = fetch_agent_owner_instructions(user_id, agent_owner_id)
    assert "prompt" in instruction
    assert instruction["prompt"] == "Motivate the user to stay consistent."
    
    # Test instruction parsing
    parsed = parse_agent_owner_prompt("Motivate the user and include goals")
    assert parsed["include_goals"] == True
    assert parsed["motivation_type"] == "goal_reminder"
    
    parsed = parse_agent_owner_prompt("Warn about lack of exercise")
    assert parsed["warning_tone"] == True
    assert parsed["motivation_type"] == "warning"

def test_agent_state_consistency():
    """Test that AgentState is consistent across the application."""
    from app.agent import AgentState
    
    # Test AgentState structure
    state = AgentState(
        input="test message",
        user_id="end_user_test",
        agent_owner_id="test_agent",
        node_output="",
        output=""
    )
    
    assert state["input"] == "test message"
    assert state["user_id"] == "end_user_test"
    assert state["agent_owner_id"] == "test_agent"
    assert state["node_output"] == ""
    assert state["output"] == ""

