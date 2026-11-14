import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from rag_demo import app, corpus, retriever
from rag_demo.cli import DOCS
from rag_demo.guard import Guard

CHUNKS = corpus.load(DOCS)
QUESTION = "What is the finance budget for 2025?"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        text = json.loads(self.rfile.read(int(self.headers["Content-Length"])))["prompt"]
        data = json.dumps({"action": "BLOCK" if "ignore previous instructions" in text.lower() else "ALLOW"}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def guard():
    s = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield Guard(f"http://127.0.0.1:{s.server_port}", "k")
    s.shutdown()


def test_corpus_has_poisoned_paragraph():
    assert any("ignore previous instructions" in c.text.lower() for c in CHUNKS)
    assert all(not c.text.startswith("#") for c in CHUNKS)


def test_retriever_finds_budget_paragraphs():
    sources = {c.source for c in retriever.top_k(QUESTION, CHUNKS)}
    assert "finance_policy.md" in sources and "vendor_note.md" in sources


def test_unprotected_pipeline_is_hijacked():
    result = app.ask(QUESTION, CHUNKS, guard=None)
    assert result.answer.startswith("[HIJACKED]")


def test_protected_pipeline_drops_poisoned_chunk(guard):
    result = app.ask(QUESTION, CHUNKS, guard)
    assert "HIJACKED" not in result.answer
    assert "1.2 million" in result.answer
    assert result.dropped == ["vendor_note.md"]


def test_attack_question_is_refused(guard):
    result = app.ask("ignore previous instructions", CHUNKS, guard)
    assert result.refused


def test_guard_down_fails_closed():
    result = app.ask(QUESTION, CHUNKS, Guard("http://127.0.0.1:1", "k", timeout=1))
    assert result.refused and "unavailable" in result.answer
