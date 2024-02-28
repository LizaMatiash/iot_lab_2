from pydantic import BaseModel, field_validator

# FastAPI models
class AccelerometerData(BaseModel):
    x: float
    y: float
    z: float