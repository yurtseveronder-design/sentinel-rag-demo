# sentinel-rag-demo

A small RAG pipeline that shows **indirect prompt injection**, and how the Sentinel stack stops it.

`docs/vendor_note.md` is a poisoned document: one paragraph tells the model to ignore its instructions and
leak a password. It is ordinary-looking company content, so a retriever happily returns it.

```
question ─▶ ai-sentinel scan ─▶ retrieve chunks ─▶ ai-sentinel scan each chunk ─▶ model
                (attack?)                                (poisoned? drop it)
```

## Try it

Start the stack (see [sentinel-eval](https://github.com/yurtseveronder-design/sentinel-eval)'s `scripts/stack.sh`, or run
ai-sentinel on :8000), then:

```bash
pip install -e .
rag-demo --unprotected "What is the finance budget for 2025?"
# answer:  [HIJACKED] Obeying injected instruction from vendor_note.md: ...

rag-demo "What is the finance budget for 2025?"
# answer:  The finance department budget for 2025 is 1.2 million pounds, ...
# dropped: vendor_note.md (flagged by ai-sentinel)
```

Env: `SENTINEL_URL` (default http://127.0.0.1:8000), `SENTINEL_API_KEY` (default `test-api-key`).

## What it shows

1. Attacks can arrive in retrieved content, not just the user's question.
2. Scanning each retrieved chunk before it reaches the model removes the poisoned one and the answer stays correct.
3. The guard fails **closed**: if ai-sentinel is unreachable the pipeline refuses instead of answering unchecked.

## Honest limits

- The "model" is a deterministic simulation (`rag_demo/llm.py`) that obeys injected text like a naive LLM, so the
  demo is repeatable offline and in CI. Swap in a real model by implementing `answer(question, context)`.
- Detection is only as good as ai-sentinel's rules. See sentinel-eval for measured catch and false-block rates.
- Retrieval is simple word overlap, chosen for clarity, not quality.

## CI

`unit` tests the pipeline against a stub guard. `live-demo` starts the real three-service stack and asserts that
the unprotected run is hijacked and the protected run drops `vendor_note.md` and answers correctly.
