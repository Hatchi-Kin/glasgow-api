from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class StatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str = Field(..., description="Status of the operation")
    message: Optional[str] = Field(None, description="Additional message")


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str = Field(..., description="Health status")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
