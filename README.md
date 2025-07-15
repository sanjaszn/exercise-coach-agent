## Proposed File Structure

```
exercise-coach-agent/
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── main.py
│   ├── routing.py
│   ├── scheduler.py
│   ├── memory.py
│   ├── models.py
│   ├── tools.py
│   └── tests/
│       └── test_agent.py
├── .env
├── pytest.ini
├── requirements.txt
├── README.md
└── .gitignore
```

## Core Files

### `app/memory.py` - Data Storage
Simple in-memory storage for user data.
- `get(user_id)` - Retrieve user's data
- `update(user_id, data)` - Add/update user data  
- `clear(user_id)` - Delete user's data
- `set(user_id, data)` - Replace user's data completely

### `app/tools.py` - Business Logic
Core functions for exercise management.
- `should_send_exercise(user_id)` - Check if it's time to send exercise
- `should_send_reminder(user_id)` - Check if reminder is needed
- `send_exercise_fn(user_id)` - Send exercise and update memory
- `send_reminder_fn(user_id)` - Send reminder message
- `check_feedback_fn(user_id)` - Check if user provided feedback
- `schedule_session_fn(user_id, time)` - Schedule workout time

### `app/routing.py` - Decision Engine
Determines what action the agent should take.
- `route_input(user_input, user_id)` - Route to appropriate action based on input and user state

### `app/scheduler.py` - Automation
Handles automatic hourly agent execution.
- `hourly_agent_run()` - Function that runs every hour
- `start_scheduler()` - Initialize the hourly scheduler
- `set_user_schedule(time_str)` - Set user's preferred exercise time
- `schedule_session_fn(user_id, time_str)` - Agent-callable scheduling function

### `app/agent.py` - LangGraph Agent
LangGraph implementation.
- `send_exercise_node(state)` - LangGraph node to send exercise
- `send_reminder_node(state)` - LangGraph node to send reminders
- `check_feedback_node(state)` - LangGraph node to handle feedback
- `schedule_node(state)` - LangGraph node to schedule sessions
- `answer_workout_question_node(state)` - LangGraph node to answer questions
- `finalize_node(state)` - LangGraph node to add viral loop
- `route_to_node(state)` - LangGraph routing function
- `build_graph()` - Create and configure the LangGraph
- `run_agent(state)` - Execute the agent with given state

### `app/main.py` - API Server
FastAPI endpoints for user interaction.
- `schedule_exercise(time)` - POST `/schedule` - Set exercise time
- `submit_feedback(feedback)` - POST `/feedback` - Submit exercise feedback
- `get_status()` - GET `/status` - Get current exercise status
- `test_now()` - POST `/test-now` - Manually trigger agent
- `reset_session()` - POST `/reset` - Clear user data
- `root()` - GET `/` - Health check

## Configuration Files

### `app/models.py` - Data Models
Can Add Pydantic models for API validation (currently unused in single-user setup).

## Test Files

### `app/tests/test_agent.py` - API Tests
Comprehensive tests for all FastAPI endpoints and agent behavior.

### `app/tests/test_agent_graph.py` - LangGraph Tests  
(currently commented out).
