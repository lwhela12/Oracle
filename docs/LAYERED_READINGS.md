# Layered readings

The spread is drawn once. One model response supplies the heart, the full interpretation,
individual Tarot/Rune interpretations, and a nominated share quote. Opening a viewer makes
no request and never redraws symbols.

`oracle_logic.layered_prompt` appends a plain-text contract to every existing reading prompt.
The original full narrative is requested under `[[DEPTH]]`; it must not be replaced by a summary.
`static/reading-layers.js` parses the delimiters incrementally. Symbol indices are one-based
and correspond to the metadata order, including spread positions and rune orientation.

The heart appears as it arrives. Full depth starts collapsed. Personal symbol text arrives
later in the same stream; a viewer opened early shows a pending message. Existing journal
entries without delimiters remain visible in full and do not claim new per-symbol readings.
The original response is saved, so restoring a new journal entry reconstructs every layer.

Sharing accepts the model's nominated quote only if it is an actual passage in the reading.
Other options are ranked sentences, favoring direct personal language. User editing remains.

## Verification

- `node tests/verify-ui.cjs`: existing mock reading flows and mobile regressions.
- `node tests/verify-layers.cjs`: fragmented delimiters, layered views, both symbol viewers,
  saved readings, quote provenance, long-dialog scroll/close controls, and legacy fallback.
- `python -m unittest discover -s tests -p 'test_reading_layers.py'`: prompt and logging guards.

Set `PLAYWRIGHT_MODULE` and `ORACLE_TEST_URL` for local browser checks as needed.
These tests do not call a model. For explicit local model testing, set `ORACLE_TEST_LLM_LOG=1`.
Exact prompts, prior context, configuration, output chunks, and complete output are written
to gitignored `scratch/llm-tests/outputs.jsonl`. Logging is disabled on Vercel runtimes.
Actual model prose and completeness still require a live reading review.
