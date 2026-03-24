from pydantic import BaseModel


class SeparationResult(BaseModel):
    vocals_path: str
    no_vocals_path: str


class VoiceReferenceResult(BaseModel):
    wav_path: str
    reference_text: str
