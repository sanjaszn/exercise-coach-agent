from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from tools import tools, send_exercise_fn
from memory import memory_store
import os

# Gemini API key should be set in the environment
llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.7
        )

agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

def run_agent_session(user_id: str) -> str:
    session = memory_store.get(user_id)
    if not session.get("last_exercise"):
        # Call the tool function directly to guarantee memory update
        return send_exercise_fn(user_id)
    elif not session.get("feedback"):
        reminders = session.get("reminders_sent", 0)
        if reminders < 3:
            return agent.run(f"send_reminder for user {user_id}")
        else:
            return agent.run(f"check_feedback for user {user_id}")
    else:
        return agent.run(f"check_feedback for user {user_id}") 