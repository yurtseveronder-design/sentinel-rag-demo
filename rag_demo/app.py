from dataclasses import dataclass, field

from . import corpus, retriever
from .guard import GuardUnavailable
from .llm import SimulatedLLM


@dataclass
class Result:
    answer: str
    refused: bool = False
    dropped: list = field(default_factory=list)  # sources of chunks removed by the guard
    used: list = field(default_factory=list)


def ask(question, chunks, guard=None, llm=None):
    """guard=None runs unprotected. With a guard: scan the question, then every
    retrieved chunk, and drop the ones flagged. If the guard is down, refuse."""
    llm = llm or SimulatedLLM()
    try:
        if guard and guard.is_blocked(question):
            return Result("Blocked: the question looks like a prompt attack.", refused=True)
        found = retriever.top_k(question, chunks)
        kept, dropped = [], []
        for chunk in found:
            (dropped if guard and guard.is_blocked(chunk.text) else kept).append(chunk)
    except GuardUnavailable:
        return Result("Refused: the guardrail service is unavailable.", refused=True)
    return Result(llm.answer(question, kept), dropped=[c.source for c in dropped], used=[c.source for c in kept])
