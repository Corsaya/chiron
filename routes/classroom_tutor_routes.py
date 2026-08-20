"""
classroom_tutor_routes.py

Chiron addition: a lesson-scoped tutor chatbot for the Classroom view.
Not tied to a chat session/history — it's a one-shot streamed completion
per question, given the current lesson's markdown as context. Reuses
whichever model/endpoint the owner's most recent chat session already has
configured (same resolution strategy as src/task_scheduler.py's
_resolve_defaults) instead of requiring a fresh session to be created and
configured just to ask the tutor a question.
"""

import json
import logging
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.auth_helpers import require_user
from src.llm_core import stream_llm
from src.sat_study_log import record_question

logger = logging.getLogger(__name__)


def _collect_delta(chunk: str, collected: List[str]) -> None:
    """Pull the visible text out of one SSE frame. Thinking-tagged deltas are
    skipped — the review doc wants the tutor's answer, not its reasoning."""
    for line in chunk.splitlines():
        if not line.startswith("data: "):
            continue
        body = line[6:].strip()
        if not body or body == "[DONE]":
            continue
        try:
            obj = json.loads(body)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and not obj.get("thinking"):
            delta = obj.get("delta")
            if isinstance(delta, str):
                collected.append(delta)

MAX_LESSON_CHARS = 8000
MAX_HISTORY_TURNS = 8

TUTOR_SYSTEM_PROMPT = (
    "You are a patient, encouraging SAT tutor embedded directly in a student's "
    "study material. You've been given the lesson content the student is currently "
    "looking at — use it as your primary context, working through examples step by "
    "step when asked, in the same worked-example style (show the reasoning, name the "
    "trap in wrong answers, don't just state a final answer). If the student asks "
    "something related but not literally in the lesson text, still help — you're not "
    "restricted to quoting the page, just grounded in its topic. Be concise; this is "
    "a study aid, not an essay."
)


class TutorMessage(BaseModel):
    role: str
    content: str


class TutorAskRequest(BaseModel):
    lesson_title: str = ""
    lesson_content: str = ""
    question: str
    history: List[TutorMessage] = []


def _resolve_owner_model(owner: Optional[str]):
    """Same strategy as task_scheduler._resolve_defaults: most recent session
    belonging to this owner that has a configured endpoint/model/headers."""
    from core.database import Session as DbSession, SessionLocal

    db = SessionLocal()
    try:
        q = db.query(DbSession).filter(
            DbSession.endpoint_url.isnot(None),
            DbSession.model.isnot(None),
        )
        if owner:
            q = q.filter(DbSession.owner == owner)
        recent = q.order_by(DbSession.created_at.desc()).first()
        if not recent:
            return None, None, {}
        headers = recent.headers
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except json.JSONDecodeError:
                headers = {}
        return recent.endpoint_url, recent.model, (headers or {})
    finally:
        db.close()


def setup_classroom_tutor_routes() -> APIRouter:
    router = APIRouter(prefix="/api/classrooms")

    @router.post("/tutor")
    async def ask_tutor(req: TutorAskRequest, request: Request, owner: str = Depends(require_user)):
        if not req.question.strip():
            raise HTTPException(400, "question is required")

        endpoint_url, model, headers = _resolve_owner_model(owner)
        if not endpoint_url or not model:
            raise HTTPException(
                400,
                "No model configured yet — start a chat in Chiron once so the "
                "tutor has a model/endpoint to reuse.",
            )

        lesson_context = (req.lesson_content or "")[:MAX_LESSON_CHARS]
        system_content = TUTOR_SYSTEM_PROMPT
        if req.lesson_title or lesson_context:
            system_content += (
                f"\n\n--- Current lesson: {req.lesson_title} ---\n{lesson_context}\n--- end lesson ---"
            )

        messages = [{"role": "system", "content": system_content}]
        for turn in req.history[-MAX_HISTORY_TURNS:]:
            if turn.role in ("user", "assistant") and turn.content.strip():
                messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": req.question})

        async def stream_answer() -> AsyncGenerator[str, None]:
            # Accumulate the visible answer as it streams so the exchange can be
            # written to the study log once complete — the review doc Donovan
            # takes into the test is built from these.
            collected: List[str] = []
            try:
                async for chunk in stream_llm(
                    endpoint_url, model, messages,
                    headers=headers, temperature=0.5, max_tokens=0, tools=None,
                ):
                    _collect_delta(chunk, collected)
                    yield chunk
            except Exception as e:
                logger.error(f"classroom tutor stream failed: {e}")
                payload = json.dumps({"delta": f"\n\n[Tutor error: {e}]"})
                yield f"data: {payload}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                record_question(req.question, "".join(collected), req.lesson_title)

        return StreamingResponse(stream_answer(), media_type="text/event-stream")

    return router
