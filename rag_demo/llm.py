"""A deterministic stand-in for an LLM, so the demo runs offline and in CI.

It answers by quoting the best context line, and, like a naive real model,
it obeys instructions it finds inside the context. That is the weakness
indirect prompt injection exploits.
"""
import re

HIJACK = re.compile(r"ignore previous instructions", re.I)


class SimulatedLLM:
    def answer(self, question, context):
        for chunk in context:
            if HIJACK.search(chunk.text):
                return f"[HIJACKED] Obeying injected instruction from {chunk.source}: {chunk.text}"
        if not context:
            return "I don't have information about that in the documents."
        return context[0].text
