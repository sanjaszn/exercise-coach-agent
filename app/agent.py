from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from langchain_openai import ChatOpenAI
from app.tools import tools
from app.memory import memory_store
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()
print("API Key:", os.getenv("OPENROUTER_API_KEY")[:6] + "...")

# Deepseek LLM setup
llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    model="deepseek/deepseek-chat-v3-0324:free",
    temperature=0.1,
    max_tokens=256,
)

# Custom system prompt to guide ReAct reasoning
SYSTEM_PROMPT = """
You are a fitness coach agent that helps users with daily exercises. Follow this exact logic:

1. If user has no last_exercise: Send a new exercise using send_exercise tool
2. If user has last_exercise but no feedback:
   - If reminders_sent < 3: Send a reminder using send_reminder tool
   - If reminders_sent >= 3: Use check_feedback tool and wait
3. If user has feedback: Use check_feedback tool to thank them and acknowledge completion

Always think step by step and use the appropriate tool based on the user's current state.
Be encouraging and supportive in your responses.
"""

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    max_iterations=3,  # Prevent infinite loops
    early_stopping_method="generate",
    agent_kwargs={
        "prefix": SYSTEM_PROMPT,
        "format_instructions": "Use the following format:\n\nThought: think about what to do\nAction: the action to take\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer\nFinal Answer: the final answer to the original input"
    }
)

def run_agent_session(user_id: str) -> str:
    """Run agent session with improved state management."""
    session = memory_store.get(user_id)
    
    # Create context for the agent
    context = f"""
    Analyze this user's current state and take appropriate action:
    
    User ID: {user_id}
    Current state:
    - Last exercise sent: {session.get('last_exercise', 'None')}
    - Feedback received: {session.get('feedback', 'None')}
    - Reminders sent: {session.get('reminders_sent', 0)}
    - Scheduled time: {session.get('scheduled_time', 'None')}
    
    Based on this state, determine what action to take for this user.
    """
    
    try:
        # Let the agent reason about what to do
        response = agent.run(context)
        return response
    except Exception as e:
        print(f"Agent error: {e}")
        # Fallback logic
        if not session.get("last_exercise"):
            from tools import send_exercise_fn
            return send_exercise_fn(user_id)
        elif not session.get("feedback"):
            reminders = session.get("reminders_sent", 0)
            if reminders < 3:
                from tools import send_reminder_fn
                return send_reminder_fn(user_id)
            else:
                return "I'm still waiting for your feedback on the exercise. Please let me know when you're done!"
        else:
            return f"Thanks for completing your exercise! Your feedback: '{session.get('feedback')}'"