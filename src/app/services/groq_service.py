import json
import re
from json import JSONDecodeError

from fastapi import HTTPException, status
from groq import APIError, AsyncGroq
from pydantic import ValidationError

from src.app.core.config import get_settings
from src.app.schemas.voice import (
    InstructionPayload,
    TaskCreate,
    TaskReplace,
    TaskUpdate,
)

_TASK_ID_ENDPOINT = re.compile(r"^/tasks/([1-9][0-9]*)$")
_SYSTEM_PROMPT = """You route voice commands to the task API.
Return only one valid JSON object, with no markdown or additional text, in
exactly this shape: {"endpoint": "/tasks", "method": "POST", "params": {"title": "Buy milk"}}.
Choose the endpoint, HTTP method, and parameters based on the user's requested
task operation. Supported operations:
- List tasks: GET /tasks, params {}
- Create a task: POST /tasks, params {"title": string, "done": boolean optional}
- Replace a task: PUT /tasks/{task_id}, params {"title": string, "done": boolean}
- Partially update a task: PATCH /tasks/{task_id}, params containing title,
  done, or both
- Delete a task: DELETE /tasks/{task_id}, params {}
For operations on an existing task, put its integer ID in the endpoint path.
Never include an ID in params. Do not invent missing titles or task IDs.
"""


def create_groq_client() -> AsyncGroq:
    settings = get_settings()
    if not settings.groq_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Groq is not configured. Set GROQ_API_KEY in the server environment.",
        )
    return AsyncGroq(
        api_key=settings.groq_api_key,
        timeout=settings.request_timeout_seconds,
    )


async def get_instruction(
    client: AsyncGroq,
    transcription: str,
) -> InstructionPayload:
    settings = get_settings()
    try:
        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": transcription},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq could not generate a task instruction.",
        ) from exc

    content = response.choices[0].message.content if response.choices else None
    try:
        if not content:
            raise ValueError("Groq returned an empty response.")
        payload = InstructionPayload.model_validate(json.loads(content))
        return validate_instruction(payload)
    except (JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq returned an invalid task instruction.",
        ) from exc


async def transcribe_audio(
    client: AsyncGroq,
    filename: str,
    audio: bytes,
    content_type: str,
    language: str | None,
) -> str:
    settings = get_settings()
    request_options: dict[str, object] = {
        "file": (filename, audio, content_type),
        "model": settings.groq_transcription_model,
    }
    if language:
        request_options["language"] = language
    try:
        response = await client.audio.transcriptions.create(**request_options)
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq could not transcribe the audio.",
        ) from exc

    transcription = response.text.strip()
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Groq returned an empty transcription.",
        )
    return transcription


def validate_instruction(payload: InstructionPayload) -> InstructionPayload:
    method = payload.method.upper()
    params = payload.params

    if payload.endpoint == "/tasks":
        if method == "GET":
            _require_empty_params(params)
        elif method == "POST":
            params = TaskCreate.model_validate(params).model_dump()
        else:
            raise ValueError("Unsupported method for /tasks.")
    else:
        match = _TASK_ID_ENDPOINT.fullmatch(payload.endpoint)
        if match is None:
            raise ValueError("Unsupported task endpoint.")
        task_id = int(match.group(1))
        if method == "PUT":
            params = TaskReplace.model_validate(params).model_dump()
        elif method == "PATCH":
            params = TaskUpdate.model_validate(params).model_dump(
                exclude_unset=True
            )
        elif method == "DELETE":
            _require_empty_params(params)
        else:
            raise ValueError("Unsupported method for a task ID.")
        if task_id < 1:
            raise ValueError("Invalid task ID.")

    return payload.model_copy(update={"method": method, "params": params})


def _require_empty_params(params: dict[str, object]) -> None:
    if params:
        raise ValueError("This operation does not accept parameters.")
