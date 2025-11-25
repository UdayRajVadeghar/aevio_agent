from typing import Any, Optional


class _AgentEngineMemories:
    def create(self, *args: Any, **kwargs: Any) -> Any: ...
    def generate(self, *args: Any, **kwargs: Any) -> Any: ...


class _AgentEngines:
    memories: _AgentEngineMemories

    def create(self, *args: Any, **kwargs: Any) -> Any: ...


class Client:
    agent_engines: _AgentEngines

    def __init__(
        self,
        *,
        api_key: Optional[str] = ...,
        credentials: Any | None = ...,
        project: Optional[str] = ...,
        location: Optional[str] = ...,
        **kwargs: Any,
    ) -> None: ...

types: Any

