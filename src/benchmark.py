from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import shutil
from statistics import mean
from typing import Any
import unicodedata

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config

@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int

def _norm(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()

def load_conversations(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))

def recall_points(answer: str, expected: list[str]) -> float:
    if not expected:
        return 0.0
    answer_n = _norm(answer)
    matched = sum(1 for item in expected if _norm(item) in answer_n)
    return 1.0 if matched else 0.0

def heuristic_quality(answer: str, expected: list[str]) -> float:
    answer_n = _norm(answer)
    expected_n = [_norm(item) for item in expected]
    score = 0.0
    if answer_n and any(item in answer_n for item in expected_n):
        score += 0.3
    if all(item in answer_n for item in expected_n):
        score += 0.4
    if not any(bad in answer_n for bad in ["backend engineer", "da nang", "hue"] if bad not in expected_n):
        score += 0.2
    if any(tok in answer_n for tok in ["bullet", "- ", "ngan gon", "ngan"]):
        score += 0.1
    return min(1.0, score)

def _new_isolated_config(base_dir: Path, state_name: str):
    config = load_config(base_dir)
    state_path = config.state_dir / state_name
    if state_path.exists():
        shutil.rmtree(state_path)
    state_path.mkdir(parents=True, exist_ok=True)
    config.state_dir = state_path
    return config

def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    initial_sizes = {}
    recall_scores = []
    quality_scores = []
    for conv in conversations:
        user_id = conv["user_id"]
        if hasattr(agent, "memory_file_size"):
            initial_sizes.setdefault(user_id, agent.memory_file_size(user_id))
        thread_id = f"{conv['id']}-thread"
        for turn in conv["turns"]:
            agent.reply(user_id, thread_id, turn)
        for idx, question in enumerate(conv.get("recall_questions", [])):
            recall_thread = f"{conv['id']}-recall-{idx}"
            resp = agent.reply(user_id, recall_thread, question["question"])
            answer = resp["answer"]
            recall_scores.append(recall_points(answer, question["expected_contains"]))
            quality_scores.append(heuristic_quality(answer, question["expected_contains"]))
    memory_growth = 0
    if hasattr(agent, "memory_file_size") and conversations:
        user_ids = {conv["user_id"] for conv in conversations}
        initial_total = sum(initial_sizes.get(user_id, 0) for user_id in user_ids)
        final_total = sum(agent.memory_file_size(user_id) for user_id in user_ids)
        memory_growth = max(0, final_total - initial_total)
    total_agent_tokens = 0
    total_prompt_tokens = 0
    total_compactions = 0
    for conv in conversations:
        tid = f"{conv['id']}-thread"
        total_agent_tokens += agent.token_usage(tid)
        total_prompt_tokens += agent.prompt_token_usage(tid)
        if hasattr(agent, "compaction_count"):
            total_compactions += agent.compaction_count(tid)
    return BenchmarkRow(agent_name, total_agent_tokens, total_prompt_tokens, mean(recall_scores) if recall_scores else 0.0, mean(quality_scores) if quality_scores else 0.0, memory_growth, total_compactions)

def format_rows(rows: list[BenchmarkRow]) -> str:
    headers = ["Agent", "Agent tokens only", "Prompt tokens processed", "Cross-session recall", "Response quality", "Memory growth (bytes)", "Compactions"]
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        lines.append(f"| {row.agent_name} | {row.agent_tokens_only} | {row.prompt_tokens_processed} | {row.recall_score:.2f} | {row.response_quality:.2f} | {row.memory_growth_bytes} | {row.compactions} |")
    return "\n".join(lines)

def _run_suite(config, conversations, suite_name: str) -> list[BenchmarkRow]:
    baseline_cfg = _new_isolated_config(config.base_dir, f"{suite_name}-baseline")
    advanced_cfg = _new_isolated_config(config.base_dir, f"{suite_name}-advanced")
    baseline = BaselineAgent(baseline_cfg, force_offline=True)
    advanced = AdvancedAgent(advanced_cfg, force_offline=True)
    return [
        run_agent_benchmark("Baseline", baseline, conversations, baseline_cfg),
        run_agent_benchmark("Advanced", advanced, conversations, advanced_cfg),
    ]

def main() -> None:
    config = load_config(Path(__file__).resolve().parent.parent)
    standard = load_conversations(config.data_dir / "conversations.json")
    stress = load_conversations(config.data_dir / "advanced_long_context.json")
    standard_rows = _run_suite(config, standard, "standard")
    stress_rows = _run_suite(config, stress, "stress")
    print("=== Standard Benchmark ===\n")
    print(format_rows(standard_rows))
    print("\n=== Long-Context Stress Benchmark ===\n")
    print(format_rows(stress_rows))

if __name__ == "__main__":
    main()


