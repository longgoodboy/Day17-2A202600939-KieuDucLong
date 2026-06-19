# Day 17 Lab Steps

## Phase 1: Environment and Config
- Load environment variables safely.
- Create `state/` automatically if missing.
- Set offline-friendly defaults for model/provider and compact memory.
- Confirm config works without `.env`.

Checkpoint:
- `load_config()` returns a complete config object.
- Repo can run offline without API keys.

## Phase 2: Memory Primitives
- Implement a deterministic token estimator.
- Implement `UserProfileStore` for `User.md` read/write/edit/file size.
- Implement structured fact extraction from user messages.
- Implement markdown upsert so newer facts replace older ones.
- Implement compact memory summary and retention policy.

Checkpoint:
- `User.md` can be created, updated, and parsed.
- Compaction triggers when the threshold is exceeded.

## Phase 3: Baseline Agent
- Keep memory only within the current thread.
- Never read or write `User.md`.
- Provide deterministic offline replies.
- Track token usage and prompt token usage.

Checkpoint:
- Baseline remembers thread history.
- Baseline forgets across sessions by design.

## Phase 4: Advanced Agent
- Extract stable facts from each user message.
- Persist confident facts into `User.md`.
- Read `User.md` to answer cross-session recall questions.
- Append conversation turns into compact memory.
- Use summary + recent turns instead of full history when threads grow long.
- Apply correction handling so newer facts overwrite older ones.
- Block low-confidence noise, questions, and joke-like text from being stored.

Checkpoint:
- Advanced recalls name, location, profession, preferences, and style across sessions.
- Advanced handles corrections by overwriting old facts.
- Advanced compacts long threads and reduces prompt token load.
- Advanced does not pollute `User.md` with user questions.

## Phase 5: Benchmark
- Load `data/conversations.json` for the standard benchmark.
- Load `data/advanced_long_context.json` for the stress benchmark.
- Reset or isolate state before each benchmark suite.
- Run Baseline and Advanced on the same inputs but with isolated state directories.
- Ensure previous `User.md` files cannot affect benchmark results.
- Compute metrics using deterministic helper functions.
- Verify benchmark thresholds from `plan.md`.
- Print comparable tables for both benchmark suites.
- Make sure the datasets include correction, follow-up, and open-thread style turns so the bonus behavior is visible.

Checkpoint:
- Benchmark output is readable and directly comparable.
- Stress run shows advanced compaction and lower prompt token usage.
- Benchmark data makes the bonus logic testable, not theoretical.
- Advanced recall is higher than Baseline recall in the standard benchmark.
- Advanced compactions are greater than 0 in the stress benchmark.
- Advanced prompt tokens processed are lower than Baseline in the stress benchmark.
- Benchmark results are reproducible from a clean state.

## Phase 6: Tests
- Test `User.md` read/write/edit behavior.
- Test extraction ignores questions, jokes, and noise.
- Test corrections overwrite old facts.
- Test compaction on long context.
- Test advanced cross-session recall vs baseline forgetting.
- Test advanced prompt token reduction in long-context stress.
- Test confidence threshold and conflict handling explicitly.

Checkpoint:
- Tests prove system behavior, not only happy paths.
- Bonus behavior is covered by dedicated tests.

## Phase 7: Docs and Results
- Explain how to run tests.
- Explain how to run both benchmarks.
- Record the benchmark output in the root `README.md`.
- Include a `## Results` section in `README.md` with the standard and stress benchmark tables.
- Interpret the results and trade-offs.
- Document the bonus mechanisms and known limitations.
- Summarize why the advanced agent is better on recall but more complex and stateful.

Checkpoint:
- A reviewer can understand why the submission deserves top score.
- README makes the benchmark evidence easy to inspect.

## Definition of Done
- Offline benchmark and tests run without API keys.
- Baseline and advanced behaviors are clearly different and measurable.
- Persistent memory, compact memory, and benchmark reporting all work.
- README explains the score-relevant trade-offs.
- Bonus behaviors are visible in both tests and written analysis.
