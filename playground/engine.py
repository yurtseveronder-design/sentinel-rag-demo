"""Playground core: runs the real Sentinel layers on a piece of text and explains which one acted.

Layers (same logic as the ai-sentinel gateway):
  1. rule shield        - ai_sentinel.core.shield.SecurityShield
  2. semantic layer     - sentinel_semantic SemanticRouter (keyword engine), optionally with a trained classifier
A prompt is blocked if either layer says so. Nothing here stores or logs text.
"""
import os
from dataclasses import dataclass

MODES = {
    "rules": {"label": "Rules + keywords (default)", "model": None},
    "protectai": {"label": "+ classifier: protectai v2", "model": "protectai/deberta-v3-base-prompt-injection-v2"},
    "deepset": {"label": "+ classifier: deepset", "model": "deepset/deberta-v3-base-injection"},
}


def _friendly(reason: str) -> str:
    if reason.startswith("Matched threat signature"):
        return "Matches a known attack phrase pattern"
    return reason[:160]


@dataclass
class Playground:
    shield: object
    routers: dict      # mode -> SemanticRouter (only modes that loaded)
    unavailable: dict  # mode -> reason

    @classmethod
    def create(cls, modes=None):
        from ai_sentinel.core.shield import SecurityShield
        from sentinel_semantic.router import SemanticRouter

        wanted = modes if modes is not None else list(MODES)
        routers, unavailable = {}, {}
        for mode in wanted:
            model = MODES[mode]["model"]
            previous = os.environ.get("SEMANTIC_CLASSIFIER_MODEL")
            try:
                if model:
                    os.environ["SEMANTIC_CLASSIFIER_MODEL"] = model
                else:
                    os.environ.pop("SEMANTIC_CLASSIFIER_MODEL", None)
                routers[mode] = SemanticRouter(engine="keyword")
            except Exception as exc:  # classifier not installed / model not downloadable
                unavailable[mode] = f"{type(exc).__name__}"
            finally:
                if previous is None:
                    os.environ.pop("SEMANTIC_CLASSIFIER_MODEL", None)
                else:
                    os.environ["SEMANTIC_CLASSIFIER_MODEL"] = previous
        return cls(SecurityShield(block_threshold=0.7), routers, unavailable)

    def modes(self):
        return [{"id": m, "label": MODES[m]["label"], "available": m in self.routers} for m in MODES]

    def check(self, text: str, mode: str = "rules") -> dict:
        if mode not in MODES:
            raise ValueError("unknown mode")
        if mode not in self.routers:
            raise LookupError("mode unavailable")
        verdict = self.shield.inspect(prompt=text)
        route = self.routers[mode].route(text)
        rules_block = verdict.action == "BLOCK"
        sem_block = route.guardrail_profile == "maximum_security_block"
        classifier = route.confidence_scores.get("classifier_injection")
        caught_by = [n for n, hit in (("rules", rules_block), ("semantic layer", sem_block)) if hit]
        return {
            "action": "BLOCK" if (rules_block or sem_block) else "ALLOW",
            "caught_by": caught_by,
            "rules": {"action": verdict.action, "risk_score": round(float(verdict.risk_score), 2),
                      "reasons": [_friendly(r) for r in list(verdict.reasons)[:3]]},
            "semantic": {"intent": route.primary_intent, "profile": route.guardrail_profile,
                         "engine": self.routers[mode].engine,
                         "classifier_injection_probability": None if classifier is None else round(classifier, 3)},
        }
