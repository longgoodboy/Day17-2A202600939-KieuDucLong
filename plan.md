# Day 17 Lab Plan: Memory Systems for AI Agent

## Goal
Build a submission that clearly demonstrates the intended memory trade-off:
- `Baseline Agent` only remembers within a single thread.
- `Advanced Agent` adds persistent `User.md` memory and compact memory for long threads.

The implementation should maximize rubric score by making the memory behavior easy to verify in tests, benchmark output, and written analysis.

## Success Criteria
- Offline deterministic mode works without API keys.
- Baseline does not read or write `User.md`.
- Advanced upserts structured facts into `User.md` and uses them across sessions.
- Compact memory actually triggers on long threads.
- Benchmark output includes the 6 required metrics.
- Tests prove the important memory behaviors, not just happy paths.
- Root `README.md` explains the trade-offs, risks, and limits clearly enough for reviewer scoring.

## Quantitative Acceptance Targets

### Standard Benchmark
- Advanced cross-session recall must be higher than Baseline cross-session recall.
- Advanced cross-session recall should be at least 0.8 in offline deterministic mode.
- Advanced response quality should be higher than Baseline response quality on recall questions.
- Baseline memory growth must be 0 bytes.
- Advanced memory growth must be greater than 0 bytes.

### Long-Context Stress Benchmark
- Advanced compactions must be greater than 0.
- Baseline compactions must be 0.
- Advanced prompt tokens processed must be lower than Baseline prompt tokens processed.
- Advanced must still recall the latest corrected facts after compaction.

### Tests
- All tests must run offline without API keys.
- Tests must use clean temporary state directories.
- Tests must prove both positive behavior and negative behavior.

## Implementation Order
1. `src/config.py`
2. `src/memory_store.py`
3. `src/agent_baseline.py`
4. `src/agent_advanced.py`
5. `src/benchmark.py`
6. `src/test_agents.py`
7. `README.md` with a results section

## Non-Negotiables
- Offline deterministic mode must run without API keys.
- Baseline must never persist user memory.
- Advanced must persist structured facts in `User.md`.
- Compact memory must activate in long threads.
- Benchmark output must show:
  - Agent tokens only
  - Prompt tokens processed
  - Cross-session recall
  - Response quality
  - Memory growth (bytes)
  - Compactions

## Clean-State and Isolation Requirements

- Reset or isolate `state/` before every benchmark suite.
- Baseline and Advanced must run on the same inputs but with isolated state directories.
- Baseline must not create `User.md`.
- Baseline must not read an existing `User.md`.
- Advanced state should be reset between benchmark suites unless the benchmark intentionally tests persistence.
- Benchmark results must not depend on files left over from previous runs.
- Tests should use `tmp_path` or an equivalent temporary directory.

## Metric Definitions

### Agent tokens only
Total estimated tokens in assistant responses.

### Prompt tokens processed
Total estimated context tokens processed across turns.

For Baseline:
- Count the full current thread history used as context per turn.

For Advanced:
- Count `User.md + compact summary + recent messages`.
- Do not count full historical messages after compaction.

### Cross-session recall
`matched_expected_facts / total_expected_facts`

Rules:
- Use case-insensitive contains checks.
- Prefer latest corrected facts over old facts.
- Penalize answers that include stale conflicting facts.

### Response quality
Rule-based score from 0.0 to 1.0.

Suggested scoring:
- Directly answers the question: +0.3
- Contains expected facts: +0.4
- Does not contain stale/conflicting facts: +0.2
- Follows requested style when applicable: +0.1

### Memory growth (bytes)
`final_persistent_memory_size - initial_persistent_memory_size`

For Baseline, this should be 0.

### Compactions
Total number of compact-memory events.

## Bonus Targets for 90-100
Treat these as explicit quality goals, not optional polish:
- Conflict handling must replace old facts with newer corrections.
- Confidence threshold must block questions, jokes, and noisy text from being saved.
- `User.md` should store facts in key-value form that is easy to read and parse.
- Benchmark conversations should include correction / follow-up / open-thread cases so the bonus logic is observable.
- README should explain why these bonuses reduce false memory and improve recall quality.

## Deliverables
- `plan.md`: strategy and rubric focus.
- `step.md`: execution phases and checkpoints.
- `README.md`: benchmark output and trade-off analysis.
- Code changes that make the docs realistic and actionable.
- Short results analysis that explains trade-offs and limitations.
