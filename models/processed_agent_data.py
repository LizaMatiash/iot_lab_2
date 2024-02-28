from pydantic import BaseModel, field_validator
from models.agent_data import AgentData

class ProcessedAgentData(BaseModel):
    road_state: str
    agent_data: AgentData
