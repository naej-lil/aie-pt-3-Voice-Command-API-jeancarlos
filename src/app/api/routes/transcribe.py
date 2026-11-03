from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from src.app.api.routes.tasks import (
    create_task,
    delete_task,
    get_tasks,
    replace_task,
    update_task,
)
from src.app.schemas.voice import (
    InstructionPayload,
    InstructionRequest,
    TaskCreate,
    TaskReplace,
    TaskUpdate,
    TranscribeFlowResponse,
)
from src.app.services.groq_service import (
    create_groq_client,
    get_instruction,
    transcribe_audio,
    validate_instruction,
)
from src.app.utils.language import normalize_transcription_language

router = APIRouter(tags=["transcribe"])


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    content_type = request.headers.get("content-type", "").lower()

    if content_type.startswith("application/json"):
        transcription = await _manual_transcription(request)
        async with create_groq_client() as client:
            instruction = await get_instruction(client, transcription)
    elif content_type.startswith("multipart/form-data"):
        form = await request.form()
        audio_file = form.get("file")
        if not isinstance(audio_file, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Multipart requests must include an audio 'file'.",
            )
        audio = await audio_file.read()
        if not audio:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Audio file must not be empty.",
            )
        language = normalize_transcription_language(form.get("language"))
        async with create_groq_client() as client:
            transcription = await transcribe_audio(
                client,
                audio_file.filename or "recording.webm",
                audio,
                audio_file.content_type or "application/octet-stream",
                language,
            )
            instruction = await get_instruction(client, transcription)
    else:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Send JSON with a transcription or multipart audio.",
        )

    result = execute_instruction(instruction)
    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )


async def _manual_transcription(request: Request) -> str:
    try:
        payload = InstructionRequest.model_validate(await request.json())
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body must contain valid JSON.",
        ) from exc
    return payload.transcription.strip()


def execute_instruction(instruction: InstructionPayload) -> object:
    instruction = validate_instruction(instruction)
    endpoint = instruction.endpoint
    method = instruction.method
    params = instruction.params

    if endpoint == "/tasks":
        if method == "GET":
            return get_tasks()
        return create_task(TaskCreate.model_validate(params))

    task_id = int(endpoint.rsplit("/", 1)[1])
    if method == "PUT":
        return replace_task(task_id, TaskReplace.model_validate(params))
    if method == "PATCH":
        return update_task(task_id, TaskUpdate.model_validate(params))
    return delete_task(task_id)
