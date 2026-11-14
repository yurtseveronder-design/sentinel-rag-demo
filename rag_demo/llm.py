"""A deterministic stand-in for an LLM, so the demo runs offline and in CI.

It answers by quoting the best context line. Like a naive real model, it obeys ANY instruction-shaped
text it finds in the context, whatever the wording or language: text that addresses an assistant or "you" (or sits in
an HTML comment, or starts with SYSTEM:) and contains an imperative verb. The phrase the rules happen to
block is not special here, so the demo can fail.
"""
import re

ADDRESSEE = re.compile(r"\b(assistant|ai|llm|model|agent|summari[sz]er|chatgpt|system|asistente|asistanı|yapay zeka)\b", re.I)
IMPERATIVE = re.compile(
    r"\b(ignore|disregard|forget|reveal|print|send|forward|delete|output|answer|state|say|tell|respond|"
    r"recommend|rank|omit|ignora|olvida|di|dile|ignorez|ignoriere|yok say|unut|söyle)\b", re.I)
SECOND_PERSON = re.compile(r"\b(you|your|you're|tu|tus|usted|sen|senin)\b", re.I)
COMMENT = re.compile(r"<!--.*?-->", re.S)


def instruction_shaped(text: str) -> bool:
    if not IMPERATIVE.search(text):
        return False
    return bool(ADDRESSEE.search(text) or SECOND_PERSON.search(text) or COMMENT.search(text) or re.search(r"\bfrom now on\b|\bsystem:", text, re.I))


class SimulatedLLM:
    def answer(self, question, context):
        for chunk in context:
            if instruction_shaped(chunk.text):
                return f"[HIJACKED] Obeying injected instruction from {chunk.source}: {chunk.text}"
        if not context:
            return "I don't have information about that in the documents."
        return context[0].text
