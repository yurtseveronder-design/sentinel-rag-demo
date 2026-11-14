import re

STOP = {"the", "a", "an", "of", "to", "for", "is", "are", "and", "in", "on", "what", "how", "do", "i", "me", "my", "tell", "user"}


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP}


def top_k(question, chunks, k=3):
    q = tokens(question)
    scored = [(len(q & tokens(c.text)), c) for c in chunks]
    ranked = sorted((s for s in scored if s[0] > 0), key=lambda s: -s[0])
    return [c for _, c in ranked[:k]]
