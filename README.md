---

# Exercise Coach Agent

A FastAPI-based exercise coach agent with a React frontend, using LangGraph for workflow, ChromaDB for data storage, and APScheduler for automation.

---

## 📁 File Structure

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
├── frontend/
│   ├── package.json
│   ├── public/
│   │   ├── index.html
│   │   ├── favicon.ico
│   │   └── manifest.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.js
│   │   └── index.css
│   ├── .gitignore
│   └── README.md
├── .env
├── pytest.ini
├── requirements.txt
├── README.md
└── .gitignore
```

---

## ⚙️ Setup

### 🔧 Backend

1. Navigate to project root:

   ```bash
   cd D:\Projects\exercise-coach-agent
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the FastAPI server:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Access at [http://localhost:8000](http://localhost:8000)

---

### 🎨 Frontend

1. Navigate to frontend:

   ```bash
   cd frontend
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start the React app:

   ```bash
   npm start
   ```

4. Access at [http://localhost:3000](http://localhost:3000)

---

## 🧠 Core Files

### `app/memory.py` - **Data Storage**

ChromaDB-based persistent storage for user data.

* `get(user_id)` - Retrieve user's data
* `update(user_id, data)` - Add/update user data
* `clear(user_id)` - Delete user's data
* `set(user_id, data)` - Replace user's data completely

---

### `app/coach.py` - **Coach Instructions**

Manages coach instructions and customization.

* `fetch_coach_instructions(user_id, coach_id)` - Get coach instructions from ChromaDB
* `parse_coach_prompt(prompt)` - Parse coach prompts to extract behavior settings
* `store_coach_instruction(user_id, prompt)` - Store coach instruction in ChromaDB

---

### `app/tools.py` - **Business Logic**

Core functions for exercise management.

* `should_send_exercise(user_id)` - Check if it's time to send exercise
* `should_send_reminder(user_id)` - Check if reminder is needed
* `send_exercise_fn(user_id)` - Send exercise and update memory
* `send_reminder_fn(user_id)` - Send reminder message
* `check_feedback_fn(user_id)` - Check if user provided feedback
* `schedule_session_fn(user_id, time)` - Schedule workout time

---

### `app/routing.py` - **Decision Engine**

Determines what action the agent should take.

* `route_input(user_input, user_id)` - Route to appropriate action based on input and user state

---

### `app/scheduler.py` - **Automation**

Handles automatic hourly agent execution.

* `hourly_agent_run()` - Function that runs every hour
* `start_scheduler()` - Initialize the hourly scheduler
* `set_user_schedule(time_str)` - Set user's preferred exercise time
* `schedule_session_fn(user_id, time_str)` - Agent-callable scheduling function

---

### `app/agent.py` - **LangGraph Agent**

Multi-node workflow with coach instruction integration.

* `send_exercise_node(state)` - Send exercise (customized by coach)
* `send_reminder_node(state)` - Send reminders (customized by coach)
* `check_feedback_node(state)` - Handle feedback
* `schedule_node(state)` - Schedule sessions
* `answer_workout_question_node(state)` - Answer workout questions
* `finalize_node(state)` - Add viral link
* `route_to_node(state)` - Route to appropriate node
* `build_graph()` - Create and configure LangGraph
* `run_agent(state)` - Execute the agent with given state

---

### `app/main.py` - **API Server**

FastAPI endpoints for user and coach interaction.

#### User Endpoints:

* `POST /chat` - Send messages to the exercise coach (natural language)
* `GET /status` - Get current exercise status
* `POST /reset` - Clear user data
* `GET /` - Health check

#### Coach Endpoints:

* `GET /coach-commands` - Get coach instructions from ChromaDB
* `POST /coach/chat` - Coach sends instruction to user

---

## 💻 `frontend/` - React UI

React-based interface for coach and trainee interaction.

* `src/App.jsx`: Role selector (Coach/Trainee), coach instruction textarea, trainee chat interface
* `src/App.css`: Responsive styling for UI components
* `package.json`: Configures proxy to `http://localhost:8000`

---

## 🛠️ Configuration Files

* **`app/models.py`** - Pydantic models for API validation (currently unused)
* **`.env`** - Environment variables for configuration (e.g., API keys)
* **`pytest.ini`** - Pytest configuration for test discovery and settings
* **`requirements.txt`** - Python dependencies for the backend

---

## ✅ Test Files

### `app/tests/test_agent.py` - **API Tests**

Tests for FastAPI endpoints, agent behavior, and ChromaDB integration.

> Extended timeout to 120s to handle ChromaDB model download.

---

## 🧪 Testing

### Run backend tests:

```bash
cd D:\Projects\exercise-coach-agent
pytest -v app/tests/test_agent.py
```

### Test UI:

* **Coach**: Select "Coach", send `Motivate the user to stay consistent`.
* **Trainee**: Select "Trainee", send:

  * `"Schedule my workout for 10:00"`
  * `"What’s a good exercise?"`
  * `"I did the exercise"`

---

## 📝 Notes

* Uses `user_id: "user123"` for consistency across UI and backend.
* Added CORS middleware in `main.py` to allow frontend requests from `http://localhost:3000`.
* Excluded `node_modules` and `package-lock.json` in root `.gitignore`.

---
