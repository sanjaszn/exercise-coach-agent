import uuid
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from app.memory import memory_store
import os
import logging

logger = logging.getLogger(__name__)

# Initialize LLM
llm = ChatOpenAI(
    model="deepseek/deepseek-chat-v3-0324:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    temperature=0.3,
    max_tokens=1000,
    timeout=30,
)

def create_agent_from_description(description: str) -> dict:
    """Create a new agent from user description"""
    # Validate description
    if not description or not description.strip():
        raise ValueError("Description cannot be empty")
    
    agent_id = str(uuid.uuid4())
    
    # Parse user description to create agent config
    agent_config = parse_agent_description(description)
    
    # Initialize agent state in memory
    memory_store.set(agent_id, {
        "agent_id": agent_id,
        "description": description,
        "config": agent_config,
        "created_at": datetime.now().isoformat(),
        "status": "active"
    })
    
    logger.info(f"Created agent {agent_id} with config: {agent_config}")
    
    return {
        "agent_id": agent_id,
        "config": agent_config
    }

def parse_agent_description(description: str) -> dict:
    """Use LLM to parse user description into agent configuration"""
    
    prompt = f"""
    Parse this agent description and create a simple configuration:

    Description: "{description}"

    Return JSON with this structure:
    {{
        "name": "Agent name (2-3 words)",
        "personality": "Main personality (e.g., 'motivational', 'supportive', 'professional')",
        "tone": "Communication style (e.g., 'friendly', 'formal', 'casual')",
        "domain": "Main area (e.g., 'fitness', 'business', 'general')",
        "features": {{
            "reminders": true/false,
            "goal_tracking": true/false,
            "progress_reports": true/false
        }}
    }}

    Respond with ONLY the JSON, no other text.
    """
    
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # Clean response
        if content.startswith("```json"):
            content = content[7:-3]
        
        return json.loads(content)
        
    except Exception as e:
        logger.error(f"Error parsing agent description: {e}")
        # Fallback config if LLM fails
        return {
            "name": "AI Assistant",
            "personality": "helpful",
            "tone": "friendly", 
            "domain": "general",
            "features": {
                "reminders": True,
                "goal_tracking": False,
                "progress_reports": False
            }
        }