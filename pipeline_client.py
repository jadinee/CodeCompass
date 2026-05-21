import os
import anthropic
from typing import Optional

_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("ROCKETRIDE_ANTHROPIC_KEY") or os.getenv("ROCKETRIDE_APIKEY")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


async def call_pipeline(project_context: str, conversation_history: list = None) -> Optional[str]:
    client = get_client()

    # Step 1: Analyze
    analysis = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system="You are a senior software engineer. Analyze the project and summarize: what it does, project type, complexity (beginner/intermediate/advanced), languages, and frameworks. Be concise.",
        messages=[{"role": "user", "content": "Analyze this project:\n\n" + project_context[:4000]}]
    )
    analysis_text = analysis.content[0].text

    # Step 2: Knowledge Gaps
    gaps = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system="You are an expert coding educator. Given a project analysis, identify what the builder likely understands and what they probably have gaps in. Be specific to the technologies.",
        messages=[{"role": "user", "content": "Project analysis:\n" + analysis_text + "\n\nIdentify knowledge gaps."}]
    )
    gaps_text = gaps.content[0].text

    # Step 3: Learning Guide
    guide = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1200,
        system="You are CodeCompass, a warm AI mentor. Generate a personalized learning guide using EXACTLY this structure:\n\n**\U0001f9ed What You Built**\n[2-3 sentence description]\n\n**\U0001f6e0\ufe0f Tech Stack**\n[list the technologies]\n\n**\u2705 You Likely Know**\n[list concepts they probably understand]\n\n**\U0001f4da Worth Learning More**\n[list knowledge gaps with one sentence why each matters]\n\n**\U0001f4a1 Choose Your Path**\nA. [specific learning action]\nB. [specific learning action]\nC. [specific learning action]\nD. Ask your own question",
        messages=[{"role": "user", "content": "Analysis:\n" + analysis_text + "\n\nGaps:\n" + gaps_text + "\n\nGenerate the learning guide."}]
    )

    return guide.content[0].text


async def call_followup(question: str, project_context: str, previous_analysis: str) -> Optional[str]:
    client = get_client()

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        system="You are CodeCompass, a helpful AI coding mentor. Answer the user's question about their project clearly and practically.",
        messages=[{"role": "user", "content": "My project:\n" + project_context[:2000] + "\n\nPrevious analysis:\n" + previous_analysis[:1000] + "\n\nMy question: " + question}]
    )

    return response.content[0].text
