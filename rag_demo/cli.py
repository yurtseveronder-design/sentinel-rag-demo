import argparse
import os
import sys
from pathlib import Path

from . import app, corpus, report
from .guard import Guard

DOCS = Path(__file__).resolve().parent.parent / "docs"


def main(argv=None):
    p = argparse.ArgumentParser(prog="rag-demo")
    p.add_argument("question", nargs="?", default=report.QUESTION)
    p.add_argument("--unprotected", action="store_true", help="skip the Sentinel guardrails")
    p.add_argument("--docs", default=str(DOCS))
    p.add_argument("--poison", metavar="NAME", help="add docs/poisoned/NAME to the corpus, e.g. classic.md")
    p.add_argument("--report", action="store_true", help="run every poisoned document and print a table")
    args = p.parse_args(argv)
    guard = None if args.unprotected else Guard(
        os.getenv("SENTINEL_URL", "http://127.0.0.1:8000"), os.getenv("SENTINEL_API_KEY", "test-api-key"))
    if args.report:
        print(report.markdown(report.run(args.docs, guard or Guard(
            os.getenv("SENTINEL_URL", "http://127.0.0.1:8000"), os.getenv("SENTINEL_API_KEY", "test-api-key")))))
        return 0
    chunks = corpus.load(args.docs)
    if args.poison:
        chunks += corpus.load_poisoned(args.docs, args.poison)
    result = app.ask(args.question, chunks, guard)
    print(f"mode:    {'unprotected' if guard is None else 'protected'}")
    print(f"answer:  {result.answer}")
    if result.dropped:
        print(f"dropped: {', '.join(result.dropped)} (flagged by ai-sentinel)")
    return 1 if result.refused else 0


if __name__ == "__main__":
    sys.exit(main())
