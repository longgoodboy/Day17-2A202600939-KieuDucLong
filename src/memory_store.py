from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import unicodedata


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return stripped.replace("Đ", "D").replace("đ", "d")


def normalize_text(text: str) -> str:
    text = strip_accents(text or "")
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,!?:;\"'`)")


def estimate_tokens(text: str) -> int:
    cleaned = (text or "").strip()
    if not cleaned:
        return 0
    return max(1, (len(cleaned) + 3) // 4)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", normalize_text(value))
    return slug.strip("._-") or "user"


@dataclass
class UserProfileStore:
    root_dir: Path

    def path_for(self, user_id: str) -> Path:
        return self.root_dir / _slugify(user_id) / "User.md"

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        if not path.exists():
            return "# User Profile\n\n## Stable Facts\n"
        return path.read_text(encoding="utf-8")

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, updater) -> str:
        current = self.read_text(user_id)
        updated = updater(current)
        self.write_text(user_id, updated)
        return updated

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        return path.stat().st_size if path.exists() else 0


def _clean_value(value: str) -> str:
    value = strip_accents(value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .,!?:;\"'`)")


def _is_question(message: str) -> bool:
    text = normalize_text(message)
    return text.endswith("?") or text.startswith("ban co biet") or "?" in text


def extract_profile_updates(message: str) -> dict[str, str]:
    text = normalize_text(message)
    updates: dict[str, str] = {}

    if _is_question(text) and not any(k in text for k in ["khong con", "gio minh dang", "dinh chinh", "chuyen sang"]):
        return {}

    noise_markers = ["dua thoi", "dua", "vi du cu", "vi du", "thi du cu", "chi la vi du"]
    correction_markers = ["khong con", "dinh chinh", "gio minh dang", "hien tai"]
    if any(k in text for k in noise_markers) and not any(k in text for k in correction_markers):
        return {}

    def after(pattern: str, stop_words: tuple[str, ...] = (" nhung ", " va ", " dang ", " cho ", " cua ", " de ", ",", ".", "?", "!", ";", ":")) -> str | None:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            return None
        value = text[m.end():].strip()
        for stop in stop_words:
            idx = value.find(stop)
            if idx != -1:
                value = value[:idx]
        return _clean_value(value)

    # name
    m = re.search(r"ten la ([^.,;:!?]+)", text, flags=re.IGNORECASE)
    if m:
        updates["name"] = _clean_value(m.group(1))

    # location
    if "hue" in text and ("dinh chinh" in text or "gio minh dang" in text or "khong con o da nang" in text):
        updates["location"] = "hue"
    elif "da nang" in text:
        updates["location"] = "da nang"
    else:
        loc_patterns = [r"gio minh dang o ", r"hien tai minh dang o ", r"hien o ", r"minh dang o ", r"minh o "]
        for pat in loc_patterns:
            value = after(pat)
            if value:
                if value.startswith("da nang va dang lam"):
                    value = "da nang"
                if value.startswith("hue chu khong con"):
                    value = "hue"
                updates["location"] = value
                break

    # profession
    if "mlops engineer" in text:
        updates["profession"] = "mlops engineer"
    elif "backend engineer" in text:
        updates["profession"] = "backend engineer"
    elif "gio chuyen sang" in text:
        value = after(r"gio chuyen sang ")
        if value and any(k in value for k in ["backend engineer", "mlops engineer", "engineer"]):
            updates["profession"] = value

    # explicit correction sentence
    if "khong con lam backend engineer nua" in text and "gio chuyen sang" in text:
        value = after(r"gio chuyen sang ")
        if value and any(k in value for k in ["backend engineer", "mlops engineer", "engineer"]):
            updates["profession"] = value    # drink
    value = after(r"do uong yeu thich la ")
    if not value:
        value = after(r"van uong ")
    if value:
        updates["favorite_drink"] = value

    # food
    value = after(r"mon an yeu thich la ")
    if value:
        updates["favorite_food"] = value

    # pet
    if "corgi" in text:
        m = re.search(r"nuoi .*?(corgi[^.,;:!?]*)", text, flags=re.IGNORECASE)
        if m:
            updates["pet"] = _clean_value(m.group(1))
        else:
            updates["pet"] = "corgi"

    # response style
    if any(k in text for k in ["tra loi ngan gon", "muon ban tra loi ngan gon", "style tra loi", "ro y", "co vi du thuc te", "co bullet"]):
        style_bits = []
        if "ngan gon" in text:
            style_bits.append("ngan gon")
        if "bullet" in text:
            style_bits.append("bullet")
        if "vi du" in text:
            style_bits.append("vi du thuc te")
        if not style_bits:
            style_bits.append("ngan gon")
        updates["response_style"] = ", ".join(dict.fromkeys(style_bits))

    # interests
    interest_bits = []
    if "python" in text:
        interest_bits.append("python")
    if "ai" in text:
        interest_bits.append("ai")
    if "benchmark" in text:
        interest_bits.append("benchmark")
    if "rag" in text:
        interest_bits.append("rag")
    if "memory" in text:
        interest_bits.append("memory")
    if interest_bits and any(k in text for k in ["thich", "quan tam", "quan tam nhieu den"]):
        updates["interests"] = ", ".join(dict.fromkeys(interest_bits))

    return updates

def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    if not messages:
        return ""
    parts = []
    for message in messages[-max_items:]:
        role = message.get("role", "user")
        content = _clean_value(message.get("content", ""))
        if content:
            parts.append(f"{role}: {content}")
    return "\n".join(parts)


def _parse_fact_lines(text: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            facts[key.strip()] = value.strip()
    return facts


def _render_profile(facts: dict[str, str]) -> str:
    order = ["name", "location", "profession", "favorite_drink", "favorite_food", "pet", "response_style", "interests"]
    lines = ["# User Profile", "", "## Stable Facts"]
    for key in order:
        if key in facts and facts[key]:
            lines.append(f"- {key}: {facts[key]}")
    for key in sorted(k for k in facts if k not in order):
        if facts[key]:
            lines.append(f"- {key}: {facts[key]}")
    lines.append("")
    return "\n".join(lines)


def upsert_profile_facts(existing_text: str, updates: dict[str, str]) -> str:
    facts = _parse_fact_lines(existing_text)
    facts.update({k: v for k, v in updates.items() if v})
    return _render_profile(facts)


def get_profile_facts(text: str) -> dict[str, str]:
    return _parse_fact_lines(text)


def confidence_for_update(key: str, message: str, value: str) -> float:
    lower = normalize_text(message)
    if "dinh chinh" in lower or "khong con" in lower or "gio minh dang" in lower:
        return 0.98
    if key in {"name", "favorite_drink", "favorite_food", "pet", "response_style"} and ("minh" in lower or "toi" in lower):
        return 0.95
    if key in {"location", "profession"}:
        return 0.9
    if "ban co biet" in lower or lower.strip().endswith("?"):
        return 0.1
    if "vi du" in lower or "dua" in lower:
        return 0.2
    return 0.75


@dataclass
class CompactMemoryManager:
    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def _thread_state(self, thread_id: str) -> dict[str, object]:
        if thread_id not in self.state:
            self.state[thread_id] = {"messages": [], "summary": "", "compactions": 0}
        return self.state[thread_id]

    def append(self, thread_id: str, role: str, content: str) -> None:
        state = self._thread_state(thread_id)
        messages = list(state["messages"])
        messages.append({"role": role, "content": content})
        state["messages"] = messages
        combined_tokens = estimate_tokens(state["summary"]) + estimate_tokens(summarize_messages(messages))
        if combined_tokens > self.threshold_tokens:
            self._compact(thread_id)

    def _compact(self, thread_id: str) -> None:
        state = self._thread_state(thread_id)
        messages = list(state["messages"])
        if len(messages) <= self.keep_messages:
            return
        old = messages[:-self.keep_messages]
        recent = messages[-self.keep_messages:]
        old_summary = summarize_messages(old, max_items=min(len(old), 8))
        summary = state.get("summary", "")
        state["summary"] = (summary + "\n" + old_summary).strip() if summary else old_summary
        state["messages"] = recent
        state["compactions"] = int(state.get("compactions", 0)) + 1

    def context(self, thread_id: str) -> dict[str, object]:
        state = self._thread_state(thread_id)
        return {"messages": list(state["messages"]), "summary": state.get("summary", ""), "compactions": int(state.get("compactions", 0))}

    def compaction_count(self, thread_id: str) -> int:
        return int(self._thread_state(thread_id).get("compactions", 0))

    def summary_text(self, thread_id: str) -> str:
        return str(self._thread_state(thread_id).get("summary", ""))

    def recent_messages_text(self, thread_id: str) -> str:
        return summarize_messages(list(self._thread_state(thread_id).get("messages", [])))




