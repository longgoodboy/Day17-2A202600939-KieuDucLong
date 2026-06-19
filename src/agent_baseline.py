from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


from config import LabConfig, load_config
from memory_store import estimate_tokens, normalize_text
from model_provider import build_chat_model

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except Exception:
    HumanMessage = SystemMessage = None

@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0

class BaselineAgent:
    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline or self.config.force_offline
        self.sessions: dict[str, SessionState] = {}
        self.langchain_agent = None

    def _session(self, thread_id: str) -> SessionState:
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()
        return self.sessions[thread_id]

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        if not self.force_offline and self.langchain_agent is None:
            self.langchain_agent = self._maybe_build_langchain_agent()
        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self._session(thread_id).token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        return self._session(thread_id).prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        return 0

    def _reply_live(self, thread_id: str, message: str) -> dict[str, Any]:
        session = self._session(thread_id)
        session.messages.append({"role": "user", "content": message})
        prompt_tokens = sum(estimate_tokens(item["content"]) for item in session.messages)
        session.prompt_tokens_processed += prompt_tokens
        messages = [{"role": "system", "content": "You are the baseline agent. Answer only from the current thread. Keep it short."}]
        messages.extend(session.messages)
        raw = self.langchain_agent.invoke(messages)
        answer = getattr(raw, "content", None) or str(raw)
        session.messages.append({"role": "assistant", "content": answer})
        session.token_usage += estimate_tokens(answer)
        return {"answer": answer, "token_usage": session.token_usage, "prompt_token_usage": session.prompt_tokens_processed, "compactions": 0}
    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        session = self._session(thread_id)
        prompt_tokens = sum(estimate_tokens(item["content"]) for item in session.messages) + estimate_tokens(message)
        session.prompt_tokens_processed += prompt_tokens
        session.messages.append({"role": "user", "content": message})
        lower = normalize_text(message)
        if any(q in lower for q in ["ten", "name", "minh ten gi", "ten gi"]):
            answer = "Minh chi nho trong thread hien tai thoi. Neu chua co ten trong thread nay, minh khong doan."
        elif any(q in lower for q in ["o dau", "where", "hien tai", "dang o"]):
            answer = "Minh chi dung lich su trong thread hien tai, nen neu chua thay thong tin thi minh chua biet."
        elif any(q in lower for q in ["do uong", "mon an", "style", "nghe", "pet"]):
            answer = "Minh chi phan hoi dua tren nhung gi co trong thread hien tai."
        else:
            answer = "Da nhan. Minh se bam vao ngu canh cua thread nay de tra loi tiep."
        session.messages.append({"role": "assistant", "content": answer})
        session.token_usage += estimate_tokens(answer)
        return {"answer": answer, "token_usage": session.token_usage, "prompt_token_usage": session.prompt_tokens_processed, "compactions": 0}

    def _maybe_build_langchain_agent(self):
        return build_chat_model(self.config.model)



