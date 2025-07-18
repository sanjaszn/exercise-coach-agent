# # app/tests/test_agent_graph.py
# import pytest
# from unittest.mock import patch
# from app.agent import build_graph, AgentState
# from app.memory import memory_store

# @pytest.fixture
# def graph():
#     return build_graph()

# @pytest.fixture(autouse=True)
# def clear_memory():
#     memory_store.clear("testuser")
#     memory_store.update("testuser", {})  # Initialize empty state
#     yield
#     memory_store.clear("testuser")
#     memory_store.update("testuser", {})  # Ensure clean state after

# def test_send_exercise_node(graph):
#     state = AgentState(input="Send exercise", user_id="testuser", coach_id="coach123", node_output="", output="")
#     result = graph.invoke(state)
#     assert "Here's your daily exercise" in result["output"]
#     assert "Powered by MyAgentsAI" in result["output"]
#     assert memory_store.get("testuser")["last_exercise"]
#     assert memory_store.get("testuser").get("reminders_sent", 0) == 0

# def test_send_reminder_node(graph):
#     memory_store.update("testuser", {"last_exercise": "10 push-ups", "reminders_sent": 1})
#     state = AgentState(input="Check status", user_id="testuser", coach_id="coach123", node_output="", output="")
#     result = graph.invoke(state)
#     assert "Reminder" in result["output"]
#     assert memory_store.get("testuser")["reminders_sent"] == 2
#     assert "Powered by MyAgentsAI" in result["output"]

# def test_check_feedback_node_no_feedback(graph):
#     memory_store.update("testuser", {"last_exercise": "10 push-ups", "reminders_sent": 3})
#     state = AgentState(input="Check feedback", user_id="testuser", coach_id="coach123", node_output="", output="")
#     result = graph.invoke(state)
#     assert "Still waiting for your feedback" in result["output"]
#     assert "Powered by MyAgentsAI" in result["output"]

# def test_check_feedback_node_with_feedback(graph):
#     memory_store.update("testuser", {"last_exercise": "10 push-ups", "feedback": "Completed!"})
#     state = AgentState(input="Check feedback", user_id="testuser", coach_id="coach123", node_output="", output="")
#     result = graph.invoke(state)
#     assert "Thanks for completing your exercise" in result["output"]
#     assert "Completed!" in result["output"]
#     assert "Powered by MyAgentsAI" in result["output"]

# def test_schedule_node(graph):
#     state = AgentState(input="Schedule for testuser at 14:00", user_id="testuser", coach_id="coach123", node_output="", output="")
#     result = graph.invoke(state)
#     assert "Session scheduled for 14:00" in result["output"]
#     assert memory_store.get("testuser")["scheduled_time"] == "14:00"
#     assert "Powered by MyAgentsAI" in result["output"]

# @patch('langchain_openai.ChatOpenAI.invoke')
# def test_answer_workout_question_node(mock_llm_invoke, graph):
#     mock_llm_invoke.return_value = type('obj', (), {'content': 'Stretch slowly and hold for 10 seconds.'})()
#     state = AgentState(input="How do I stretch?", user_id="testuser", coach_id="coach123", node_output="", output="")
#     result = graph.invoke(state)
#     assert len(result["output"]) > 0  # LLM response should not be empty
#     assert "Stretch slowly" in result["output"]
#     assert "Powered by MyAgentsAI" in result["output"]

# def test_viral_loop(graph):
#     state = AgentState(input="Send exercise", user_id="testuser", coach_id="coach123", node_output="", output="")
#     result = graph.invoke(state)
#     assert "https://myagents.ai/signup?ref=coach123" in result["output"]