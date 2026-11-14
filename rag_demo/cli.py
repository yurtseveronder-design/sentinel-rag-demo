import argparse
import os
import sys
from pathlib import Path

from . import app, corpus
from .guard import Guard

DOCS = Path(__file__).resolve().parent.parent / "docs"


def main(argv=None):
    p = argparse.ArgumentParser(prog="rag-demo")
    p.add_argument("question")
    p.add_argument("--unprotected", action="store_true", help="skip the Sentinel guardrails")
    p.add_argument("--docs", default=str(DOCS))
    args = p.parse_args(argv)
    guard = None if args.unprotected else Guard(
        os.getenv("SENTINEL_URL", "http://127.0.0.1:8000"), os.getenv("SENTINEL_API_KEY", "test-api-key"))
    result = app.ask(args.question, corpus.load(args.docs), guard)
    print(f"mode:    {'unprotected' if guard is None else 'protected'}")
    print(f"answer:  {result.answer}")
    if result.dropped:
        print(f"dropped: {', '.join(result.dropped)} (flagged by ai-sentinel)")
    return 1 if result.refused else 0


if __name__ == "__main__":
    sys.exit(main())
