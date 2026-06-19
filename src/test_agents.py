from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from benchmark import heuristic_quality, recall_points
from config import LabConfig
from memory_store import CompactMemoryManager, UserProfileStore, extract_profile_updates, get_profile_facts
from model_provider import ProviderConfig


def make_config(tmp_path: Path):
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return LabConfig(
        base_dir=tmp_path,
        data_dir=Path(__file__).resolve().parent.parent / "data",
        state_dir=state_dir,
        compact_threshold_tokens=80,
        compact_keep_messages=2,
        model=ProviderConfig(provider="openai", model_name="dummy", temperature=0.0),
        judge_model=ProviderConfig(provider="openai", model_name="dummy", temperature=0.0),
        force_offline=True,
    )


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    store = UserProfileStore(tmp_path / "profiles")
    text = "# User Profile\n\n## Stable Facts\n- location: Da Nang\n"
    path = store.write_text("dungct", text)
    assert path.exists()
    assert "Da Nang" in store.read_text("dungct")
    updated = store.edit_text("dungct", lambda current: current.replace("Da Nang", "Hue"))
    assert "Hue" in updated
    assert store.file_size("dungct") > 0


def test_compact_trigger(tmp_path: Path) -> None:
    manager = CompactMemoryManager(threshold_tokens=20, keep_messages=2)
    thread_id = "t1"
    for i in range(6):
        manager.append(thread_id, "user", f"message number {i} with enough content to compact")
    assert manager.compaction_count(thread_id) > 0
    assert len(manager.context(thread_id)["messages"]) <= 2


def test_cross_session_recall(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    user_id = "dungct"
    baseline.reply(user_id, "a", "Mình tên là DungCT.")
    advanced.reply(user_id, "a", "Mình tên là DungCT.")
    baseline_answer = baseline.reply(user_id, "b", "Mình tên gì?")["answer"]
    advanced_answer = advanced.reply(user_id, "b", "Mình tên gì?")["answer"]
    assert "dungct" not in baseline_answer.lower()
    assert "dungct" in advanced_answer.lower()


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    baseline = BaselineAgent(config, force_offline=True)
    advanced = AdvancedAgent(config, force_offline=True)
    user_id = "dungct"
    for i in range(10):
        msg = f"turn {i} with long context about Python AI and preference {i} and extra details"
        baseline.reply(user_id, "thread", msg)
        advanced.reply(user_id, "thread", msg)
    assert advanced.prompt_token_usage("thread") < baseline.prompt_token_usage("thread")
    assert advanced.compaction_count("thread") > 0


def test_fact_extraction_ignores_questions() -> None:
    assert extract_profile_updates("Ban co biet DungCT khong?") == {}


def test_fact_extraction_ignores_jokes_and_noise(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    advanced = AdvancedAgent(config, force_offline=True)
    user_id = "dungct"
    advanced.reply(user_id, "t", "Minh hien o Hue.")
    advanced.reply(user_id, "t", "Dua thoi, minh chuyen sang product manager.")
    facts = get_profile_facts(advanced.profile_store.read_text(user_id))
    assert facts.get("profession") != "product manager"
    assert facts.get("location") == "hue"


def test_conflict_and_correction_handling(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    advanced = AdvancedAgent(config, force_offline=True)
    user_id = "dungct"
    advanced.reply(user_id, "t", "Mình ở Da Nang và làm backend engineer.")
    advanced.reply(user_id, "t", "Dinh chinh: gio minh dang o Hue va khong con lam backend engineer nua, gio chuyen sang MLOps engineer.")
    facts = get_profile_facts(advanced.profile_store.read_text(user_id))
    assert facts.get("location") == "hue"
    assert facts.get("profession") == "mlops engineer"


def test_benchmark_scoring_helpers() -> None:
    assert recall_points("dungct and coffee", ["DungCT", "coffee"]) == 1.0
    assert heuristic_quality("- dungct\n- hue", ["DungCT", "Hue"]) > 0.0


def test_clean_state_reproducibility(tmp_path: Path) -> None:
    config1 = make_config(tmp_path / "run1")
    config2 = make_config(tmp_path / "run2")
    a1 = AdvancedAgent(config1, force_offline=True)
    a2 = AdvancedAgent(config2, force_offline=True)
    a1.reply("u", "t", "Mình tên là DungCT và ở Hue.")
    a2.reply("u", "t", "Mình tên là DungCT và ở Hue.")
    assert a1.memory_file_size("u") == a2.memory_file_size("u")
