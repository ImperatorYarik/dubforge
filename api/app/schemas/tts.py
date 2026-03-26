from pydantic import BaseModel


class TtsRequest(BaseModel):
    text: str
    speaker: str
    format: str = "wav"


class VoiceSchema(BaseModel):
    name: str
    gender: str
