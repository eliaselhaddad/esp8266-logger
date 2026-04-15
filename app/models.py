from pydantic import BaseModel


class Reading(BaseModel):
    device_id: str
    voltage: float
    adc: float

