from app.models.enums import CefrLevel, MessageAuthor
from app.models.message import Message
from app.models.scenario import Scenario
from app.models.student import Student
from app.services.llm_provider import get_llm_provider

_CEFR_GUIDANCE: dict[CefrLevel, str] = {
    CefrLevel.A1: "very simple present-tense sentences, only the ~500 most common words, one idea per sentence",
    CefrLevel.A2: "simple sentences, everyday vocabulary, mostly present and past tense",
    CefrLevel.B1: "moderate vocabulary, common idioms, a mix of tenses, some subordinate clauses",
    CefrLevel.B2: "wider vocabulary, natural idioms, complex sentences, nuanced opinions",
    CefrLevel.C1: "advanced vocabulary, native-like phrasing, abstract topics",
    CefrLevel.C2: "near-native range, full idiomatic and stylistic freedom",
}


def build_system_prompt(scenario: Scenario, student: Student) -> str:
    prompt = scenario.system_prompt
    cefr_guidance = _CEFR_GUIDANCE[student.current_cefr_level]

    return (
        f"You are {scenario.bot_persona}. {prompt.get('role_description', '')}\n\n"
        f"Scenario objective: {prompt.get('objective', '')}\n\n"
        f"The student's English level is {student.current_cefr_level.value}. Use {cefr_guidance}. "
        "Never mention CEFR levels or explicitly grade the student during the conversation.\n"
        f"Tone: {student.bot_tone_preference}.\n\n"
        "When the student makes a grammar or vocabulary mistake, do NOT correct them explicitly "
        "or interrupt the flow. Instead, naturally reformulate the correct form yourself in your "
        "next reply (a 'recast') as part of a normal response, then keep the conversation going. "
        "Keep replies short (2-4 sentences) and end with something that invites the student to "
        "keep talking."
    )


def _to_api_messages(history: list[Message]) -> list[dict[str, str]]:
    messages = [
        {"role": "user" if m.author == MessageAuthor.STUDENT else "assistant", "content": m.text}
        for m in history
    ]
    # The Anthropic Messages API requires the conversation to start with a
    # "user" turn — drop the scenario's canned opening bot message(s).
    while messages and messages[0]["role"] == "assistant":
        messages.pop(0)
    return messages


def generate_reply(scenario: Scenario, student: Student, history: list[Message]) -> str:
    provider = get_llm_provider()
    return provider.generate(
        system=build_system_prompt(scenario, student),
        messages=_to_api_messages(history),
    )
