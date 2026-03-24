from pydantic import BaseModel


class ProgressEvent(BaseModel):
    step: str
    pct: int
    message: str = ""

    def to_json(self) -> str:
        return self.model_dump_json()
