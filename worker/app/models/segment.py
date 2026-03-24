from pydantic import BaseModel


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    words: list[WordTimestamp] = []
    tts_wav: str | None = None
