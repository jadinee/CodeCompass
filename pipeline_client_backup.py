import os
import nest_asyncio
nest_asyncio.apply()

from typing import Optional
from rocketride import RocketRideClient

_client: Optional[RocketRideClient] = None


async def get_client() -> RocketRideClient:
    """Get or create the RocketRide client."""
    global _client
    if _client is None:
        _client = RocketRideClient()
        await _client.connect()
        print("[RocketRide] Client connected.")
    return _client


async def call_pipeline(project_context: str, conversation_history: list = None) -> Optional[str]:
    """Send project context to RocketRide pipeline and return the response."""
    try:
        client = await get_client()
        result = await client.use(filepath='codecompass.pipe')
        token = result['token']
        response = await client.send(token, project_context)
        await client.terminate(token)
        return extract_answer(response)
    except Exception as e:
        raise RuntimeError(f"Pipeline error: {e}")


async def call_followup(question: str, project_context: str, previous_analysis: str) -> Optional[str]:
    """Send a follow-up question with full context."""
    try:
        client = await get_client()
        result = await client.use(filepath='codecompass.pipe')
        token = result['token']
        combined = (
            f"Previous project analysis:\n{previous_analysis[:2000]}\n\n"
            f"User follow-up question: {question}"
        )
        response = await client.send(token, combined)
        await client.terminate(token)
        return extract_answer(response)
    except Exception as e:
        raise RuntimeError(f"Follow-up error: {e}")


def extract_answer(data: dict) -> str:
    """Extract the answer text from RocketRide's response."""
    if not data:
        return "No response received from pipeline."
    if "answers" in data:
        answers = data["answers"]
        if isinstance(answers, list) and answers:
            item = answers[0]
            if isinstance(item, dict):
                return item.get("text", str(item))
            return str(item)
        return str(answers)
    for key in ("result", "output", "text", "message"):
        if key in data:
            return str(data[key])
    return str(data)
