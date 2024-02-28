from pydantic import BaseModel, field_validator

class GpsData(BaseModel):
    latitude: float
    longitude: float
