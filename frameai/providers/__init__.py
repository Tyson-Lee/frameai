"""Provider adapters and explicit provider selection for FrameAI."""

from .base import ProviderAdapter
from .claude import ClaudeAdapter
from .codex import CodexAdapter

_PROVIDERS: dict[str, ProviderAdapter] = {
    "claude": ClaudeAdapter(),
    "codex": CodexAdapter(),
}


def get_provider(name: str) -> ProviderAdapter:
    """Return an adapter by exact registry key."""

    try:
        return _PROVIDERS[name]
    except KeyError as exc:
        supported = ", ".join(sorted(_PROVIDERS))
        raise ValueError(
            f"unsupported provider {name!r}; choose one of: {supported}"
        ) from exc


__all__ = ["ClaudeAdapter", "CodexAdapter", "ProviderAdapter", "get_provider"]
