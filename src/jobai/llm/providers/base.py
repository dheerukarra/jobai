from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderResult:
    text: str
    in_tokens: int
    cached_tokens: int
    out_tokens: int


class Provider(Protocol):
    name: str

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None,
        max_output_tokens: int,
    ) -> ProviderResult: ...
