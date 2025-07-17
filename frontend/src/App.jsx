"use client"

import { useState, useEffect, useRef } from "react"
import axios from "axios"
import "./App.css"

const API_BASE_URL = "http://localhost:8000"
const USER_ID = "user123"

function App() {
  const [role, setRole] = useState("trainee") // Default to trainee
  const [coachInstruction, setCoachInstruction] = useState("")
  const [chatMessages, setChatMessages] = useState([])
  const [currentMessage, setCurrentMessage] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
  const chatEndRef = useRef(null)

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages])

  // Clear messages when switching roles
  const handleRoleChange = (newRole) => {
    setRole(newRole)
    setError("")
    setSuccessMessage("")
    if (newRole === "coach") {
      setCoachInstruction("")
    } else {
      setCurrentMessage("")
    }
  }

  // Handle coach instruction submission
  const handleCoachSubmit = async (e) => {
    e.preventDefault()
    if (!coachInstruction.trim()) {
      setError("Please enter an instruction")
      return
    }

    setIsLoading(true)
    setError("")
    setSuccessMessage("")

    try {
      const response = await axios.post(`${API_BASE_URL}/coach/chat`, {
        user_id: USER_ID,
        prompt: coachInstruction.trim(),
      })

      if (response.data.status === "instruction sent") {
        setSuccessMessage("Instruction sent successfully!")
        setCoachInstruction("")
      }
    } catch (err) {
      console.error("Coach submission error:", err)
      setError(err.response?.data?.detail || "Failed to send instruction. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  // Handle trainee message submission
  const handleTraineeSubmit = async (e) => {
    e.preventDefault()
    if (!currentMessage.trim()) {
      setError("Please enter a message")
      return
    }

    const userMessage = currentMessage.trim()
    setCurrentMessage("")
    setError("")
    setIsLoading(true)

    // Add user message to chat
    setChatMessages((prev) => [
      ...prev,
      {
        type: "user",
        content: userMessage,
        timestamp: new Date().toLocaleTimeString(),
      },
    ])

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: userMessage,
      })

      // Add agent response to chat
      setChatMessages((prev) => [
        ...prev,
        {
          type: "agent",
          content: response.data.response,
          timestamp: new Date().toLocaleTimeString(),
        },
      ])
    } catch (err) {
      console.error("Chat submission error:", err)
      setError(err.response?.data?.detail || "Failed to send message. Please try again.")

      // Add error message to chat
      setChatMessages((prev) => [
        ...prev,
        {
          type: "error",
          content: "Sorry, I encountered an error. Please try again.",
          timestamp: new Date().toLocaleTimeString(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Exercise Coach Agent</h1>
        <div className="role-selector">
          <label htmlFor="role-select">Select Role:</label>
          <select
            id="role-select"
            value={role}
            onChange={(e) => handleRoleChange(e.target.value)}
            className="role-dropdown"
          >
            <option value="trainee">Trainee</option>
            <option value="coach">Coach</option>
          </select>
        </div>
      </header>

      <main className="app-main">
        {error && <div className="error-message">{error}</div>}

        {successMessage && <div className="success-message">{successMessage}</div>}

        {role === "coach" ? (
          <div className="coach-interface">
            <h2>Coach Instructions</h2>
            <p className="instruction-text">Enter instructions for how the agent should behave with trainees:</p>
            <form onSubmit={handleCoachSubmit} className="coach-form">
              <textarea
                value={coachInstruction}
                onChange={(e) => setCoachInstruction(e.target.value)}
                placeholder="e.g., 'Motivate the user to stay consistent' or 'Warn about lack of exercise'"
                className="coach-textarea"
                rows="6"
                disabled={isLoading}
              />
              <button type="submit" className="submit-button" disabled={isLoading || !coachInstruction.trim()}>
                {isLoading ? "Sending..." : "Send Instruction"}
              </button>
            </form>
          </div>
        ) : (
          <div className="trainee-interface">
            <h2>Chat with Your Exercise Coach</h2>
            <div className="chat-container">
              <div className="chat-messages">
                {chatMessages.length === 0 ? (
                  <div className="welcome-message">
                    <p>Welcome! I'm your exercise coach. You can ask me about:</p>
                    <ul>
                      <li>Scheduling workouts</li>
                      <li>Exercise recommendations</li>
                      <li>Fitness questions</li>
                      <li>Progress tracking</li>
                    </ul>
                    <p>Try saying: "Schedule my workout for 10:00" or "What's a good exercise?"</p>
                  </div>
                ) : (
                  chatMessages.map((message, index) => (
                    <div key={index} className={`message ${message.type}-message`}>
                      <div className="message-content">{message.content}</div>
                      <div className="message-timestamp">{message.timestamp}</div>
                    </div>
                  ))
                )}
                <div ref={chatEndRef} />
              </div>

              <form onSubmit={handleTraineeSubmit} className="chat-form">
                <div className="chat-input-container">
                  <input
                    type="text"
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    placeholder="Type your message here..."
                    className="chat-input"
                    disabled={isLoading}
                  />
                  <button type="submit" className="send-button" disabled={isLoading || !currentMessage.trim()}>
                    {isLoading ? "..." : "Send"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
