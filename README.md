# Day 17 Lab: Memory Systems for AI Agent

## What this repo demonstrates
- Baseline agent: short-term memory only within a thread.
- Advanced agent: short-term memory + persistent `User.md` + compact memory.
- Offline deterministic mode is the default, so tests and benchmark run without API keys.
- Live API mode is supported through `.env` when you want to evaluate with a real LLM.

## How to run

```bash
pytest
python src/benchmark.py
python ui/dashboard.py
```

## Results

### Standard Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---|---|---|---|---|---|
| Baseline | 1777 | 16340 | 0.14 | 0.24 | 0 | 0 |
| Advanced | 3379 | 3275 | 0.93 | 0.58 | 221 | 0 |

### Long-Context Stress Benchmark

| Agent | Agent tokens only | Prompt tokens processed | Cross-session recall | Response quality | Memory growth (bytes) | Compactions |
|---|---|---|---|---|---|---|
| Baseline | 318 | 22917 | 0.00 | 0.20 | 0 | 0 |
| Advanced | 649 | 6461 | 1.00 | 0.40 | 154 | 26 |

## Interpretation
- Baseline is intentionally limited to within-thread memory, so its cross-session recall stays low.
- Advanced recalls stable facts from `User.md`, which is why cross-session recall is much higher.
- In the long-context stress benchmark, advanced compact memory cuts prompt tokens sharply and compacts many times, which is the main proof that the memory system is doing real work.
- Advanced memory growth is non-zero because persistent user facts are actually stored and updated.
- Response quality improves for advanced because it can answer from persistent memory rather than only the current thread.

## Trade-offs
- Advanced improves recall, but adds file growth and system complexity.
- Compact memory lowers prompt cost on long conversations, but can lose detail if summaries are too aggressive.
- Confidence thresholds reduce noise, but may skip a weakly stated fact.
- Live API mode is useful for realistic LLM behavior, but offline mode is still kept for deterministic lab validation.
