from fastapi import APIRouter

from src.app.schemas.voice import InstructionPayload, InstructionRequest
from src.app.services.groq_service import create_groq_client, get_instruction

router = APIRouter(tags=["instruction"])


@router.post("/instruction", response_model=InstructionPayload)
async def route_instruction(
    payload: InstructionRequest,
) -> InstructionPayload:
    async with create_groq_client() as client:
        return await get_instruction(client, payload.transcription.strip())
