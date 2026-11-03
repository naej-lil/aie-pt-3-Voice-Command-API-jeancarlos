from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(..., min_length=1)
    done: bool = False


class TaskReplace(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(..., min_length=1)
    done: bool


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1)
    done: bool | None = None

    @model_validator(mode="after")
    def require_update_fields(self) -> "TaskUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("'title' cannot be null.")
        if "done" in self.model_fields_set and self.done is None:
            raise ValueError("'done' cannot be null.")
        return self


class Task(BaseModel):
    id: int = Field(gt=0)
    title: str
    done: bool


class InstructionRequest(BaseModel):
    transcription: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def require_non_whitespace_transcription(self) -> "InstructionRequest":
        if not self.transcription.strip():
            raise ValueError("Transcription must not be blank.")
        return self


class InstructionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class TranscribeFlowResponse(BaseModel):
    transcription: str = Field(..., min_length=1)
    instruction: InstructionPayload
    result: Any
