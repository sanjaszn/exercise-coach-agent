from pydantic import BaseModel, Field
from typing import Optional

class ScheduleRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    time: str = Field(..., description="Time in HH:MM 24h format")

class RunNowRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")

class FeedbackRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    feedback: str = Field(..., description="User's feedback on the exercise")

class StatusResponse(BaseModel):
    user_id: str
    scheduled_time: Optional[str]
    last_exercise: Optional[str]
    feedback: Optional[str]
    reminders_sent: int
    status: str 