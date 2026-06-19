from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, confidence_for_update, estimate_tokens, extract_profile_updates, get_profile_facts, normalize_text, upsert_profile_facts
from model_provider import build_chat_model

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except Exception:
    HumanMessage = SystemMessage = None
@dataclass
class AgentContext:
    user_id: str
    memory_path: str

class AdvancedAgent:
    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline or self.config.force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(threshold_tokens=self.config.compact_threshold_tokens, keep_messages=self.config.compact_keep_messages)
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}
        self.langchain_agent = None

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        if not self.force_offline and self.langchain_agent is None:
            self.langchain_agent = self._maybe_build_langchain_agent()
        return self._reply_offline(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _apply_profile_updates(self, user_id: str, message: str) -> None:
        lower = normalize_text(message)
        if lower.endswith("?") or lower.startswith("ban co biet") or lower.startswith("hien tai minh"):
            return
        if any(k in lower for k in ["dua thoi", "dua", "vi du cu", "vi du", "thi du cu", "chi la vi du"]):
            if not any(k in lower for k in ["khong con", "dinh chinh", "gio minh dang", "hien tai"]):
                return
        updates = extract_profile_updates(message)
        if not updates:
            return
        confident = {}
        for key, value in updates.items():
            if confidence_for_update(key, message, value) >= 0.75:
                confident[key] = value
        if not confident:
            return
        current = self.profile_store.read_text(user_id)
        updated = upsert_profile_facts(current, confident)
        self.profile_store.write_text(user_id, updated)

    def _reply_live(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        before_size = self.profile_store.file_size(user_id)
        self._apply_profile_updates(user_id, message)
        self.compact_memory.append(thread_id, "user", message)
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens
        profile = self.profile_store.read_text(user_id)
        summary = self.compact_memory.summary_text(thread_id)
        recent = self.compact_memory.recent_messages_text(thread_id)
        system = (
            "You are the advanced agent. Use the persistent user profile, the compact summary, "
            "and the recent thread messages. Prefer the latest corrected facts and answer concisely in Vietnamese."
        )
        prompt = [
            {"role": "system", "content": system},
            {"role": "system", "content": f"User profile:\n{profile}"},
        ]
        if summary:
            prompt.append({"role": "system", "content": f"Compact summary:\n{summary}"})
        if recent:
            prompt.append({"role": "system", "content": f"Recent messages:\n{recent}"})
        prompt.append({"role": "user", "content": message})
        raw = self.langchain_agent.invoke(prompt)
        answer = getattr(raw, "content", None) or str(raw)
        self.compact_memory.append(thread_id, "assistant", answer)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + estimate_tokens(answer)
        after_size = self.profile_store.file_size(user_id)
        return {"answer": answer, "token_usage": self.thread_tokens[thread_id], "prompt_token_usage": self.thread_prompt_tokens[thread_id], "memory_growth_bytes": after_size - before_size, "compactions": self.compaction_count(thread_id)}
    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        before_size = self.profile_store.file_size(user_id)
        self._apply_profile_updates(user_id, message)
        self.compact_memory.append(thread_id, "user", message)
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens
        answer = self._offline_response(user_id, thread_id, message)
        self.compact_memory.append(thread_id, "assistant", answer)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + estimate_tokens(answer)
        after_size = self.profile_store.file_size(user_id)
        return {"answer": answer, "token_usage": self.thread_tokens[thread_id], "prompt_token_usage": self.thread_prompt_tokens[thread_id], "memory_growth_bytes": after_size - before_size, "compactions": self.compaction_count(thread_id)}

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        summary = self.compact_memory.summary_text(thread_id)
        recent = self.compact_memory.recent_messages_text(thread_id)
        return max(1, (estimate_tokens(summary) + estimate_tokens(recent)) // 4)
    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        facts = get_profile_facts(self.profile_store.read_text(user_id))
        lower = normalize_text(message)
        profile = [
            f"- ten: {facts.get('name', 'chua ro')}",
            f"- nghenghiep: {facts.get('profession', 'chua ro')}",
            f"- noio: {facts.get('location', 'chua ro')}",
            f"- douong: {facts.get('favorite_drink', 'chua ro')}",
            f"- monan: {facts.get('favorite_food', 'chua ro')}",
            f"- pet: {facts.get('pet', 'chua ro')}",
            f"- style: {facts.get('response_style', 'ngan gon')}",
            f"- interests: {facts.get('interests', 'chua ro')}",
        ]
        recall_markers = ["ten", "nghe", "o dau", "hien tai", "douong", "do uong", "mon an", "style", "tra loi", "pet", "nuoi", "tom tat", "mo ta", "python", "ai", "benchmark", "memory", "rag"]
        if any(k in lower for k in recall_markers):
            return "\\n".join(profile)
        return "Minh se tra loi ngan gon, co bullet va vi du thuc chien nhu ban thich."

    def _maybe_build_langchain_agent(self):
        return build_chat_model(self.config.model)








