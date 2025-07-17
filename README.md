# Exercise Coach Agent

## File Structure

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
│   ├── coach.py
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
ChromaDB-based persistent storage for user data.
- `get(user_id)` - Retrieve user's data
- `update(user_id, data)` - Add/update user data  
- `clear(user_id)` - Delete user's data
- `set(user_id, data)` - Replace user's data completely

### `app/coach.py` - Coach Instructions
Manages coach instructions and customization.
- `fetch_coach_instructions(user_id, coach_id)` - Get coach instructions from ChromaDB
- `parse_coach_prompt(prompt)` - Parse coach prompts to extract behavior settings

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
Multi-node workflow with coach instruction integration.
- `send_exercise_node(state)` - LangGraph node to send exercise (customized by coach)
- `send_reminder_node(state)` - LangGraph node to send reminders (customized by coach)
- `check_feedback_node(state)` - LangGraph node to handle feedback
- `schedule_node(state)` - LangGraph node to schedule sessions
- `answer_workout_question_node(state)` - LangGraph node to answer questions
- `finalize_node(state)` - LangGraph node to add viral loop
- `route_to_node(state)` - LangGraph routing function
- `build_graph()` - Create and configure the LangGraph
- `run_agent(state)` - Execute the agent with given state

### `app/main.py` - API Server
FastAPI endpoints for user and coach interaction.

**User Endpoints:**
- `POST /chat` - Send any message to your exercise coach (natural language)
- `GET /status` - Get current exercise status
- `POST /reset` - Clear user data
- `GET /` - Health check

**Coach Endpoints:**
- `GET /coach-commands` - Get coach instructions from ChromaDB
- `POST /coach/chat` - Coach sends instruction to user

## Configuration Files

### `app/models.py` - Data Models (not in use)
Pydantic models for API validation.

## Test Files

### `app/tests/test_agent.py` - API Tests
Comprehensive tests for all FastAPI endpoints, agent behavior, and ChromaDB integration.

