# SPDX-License-Identifier: Apache-2.0
"""One settings module. Keys come from the environment; production fails closed.

Every variable has the prefix ``COALITIONKIT_`` (for example ``COALITIONKIT_META_API_KEY``).
Keys are ``SecretStr``: they never appear in ``repr``, ``str`` or error messages.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import MissingKeyError, SettingsError

Role = Literal["gardener", "composer", "hosted_agent", "steward", "vault"]
ROLES: tuple[Role, ...] = ("gardener", "composer", "hosted_agent", "steward", "vault")
KeyName = Literal["meta", "baseten", "ollama"]
Effort = Literal["minimal", "low", "medium", "high"]
StewardProvider = Literal["meta", "baseten"]
SearchProviderName = Literal["off", "meta", "ddg", "brave"]

#: Local Ollama accepts any key; the SDK just needs a non-empty one.
LOCAL_PLACEHOLDER_KEY = "ollama"


def _default_limits() -> dict[Role, int]:
    return {"gardener": 30, "composer": 60, "hosted_agent": 120, "steward": 120, "vault": 600}


def _default_efforts() -> dict[Role, Effort]:
    return {"hosted_agent": "minimal", "composer": "low", "gardener": "low", "steward": "low"}


def _default_budgets() -> dict[Role, int]:
    return {
        "gardener": 4000,
        "composer": 4000,
        "hosted_agent": 4000,
        "steward": 4000,
        "vault": 4000,
    }


class Route:
    """Where one role's calls go. Holds no secret; the key is looked up by name."""

    __slots__ = ("base_url", "key_name", "model", "role")
    role: Role
    model: str
    base_url: str
    key_name: KeyName

    def __init__(self, role: Role, model: str, base_url: str, key_name: KeyName) -> None:
        self.role = role
        self.model = model
        self.base_url = base_url
        self.key_name = key_name

    def __repr__(self) -> str:
        return f"Route(role={self.role!r}, model={self.model!r}, base_url={self.base_url!r})"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COALITIONKIT_", extra="ignore", frozen=True)

    env: Literal["development", "test", "production"] = "development"

    meta_api_key: SecretStr | None = None
    baseten_api_key: SecretStr | None = None
    brave_api_key: SecretStr | None = None

    meta_base_url: str = "https://api.meta.ai/v1"
    baseten_base_url: str = "https://inference.baseten.co/v1"
    ollama_base_url: str = "http://localhost:11434/v1"

    gardener_model: str = "muse-wonder-1.0"
    composer_model: str = "muse-spark-1.3"
    hosted_agent_model: str = "muse-spark-1.3"
    steward_model: str = "muse-spark-1.3"
    # Default: Muse Spark Open on Baseten. Its key is required when the audit runs;
    # missing credentials must never silently select another provider's model.
    # Meta's endpoint remains available through an explicit steward_provider="meta".
    steward_provider: StewardProvider | None = None
    steward_baseten_model: str = "meta-models/muse-spark-open"

    image_model: str = "muse-image-1.0"
    segment_model: str = "sam-3.1"
    transcribe_model: str = "muse-voice-transcribe-1.0"
    media_rate_limit_per_minute: int = 120

    # Web search for agents. "off" keeps agents to what the room knows; "meta" uses the
    # Meta endpoint's built-in web search tool (Responses API), "ddg" the keyless DuckDuckGo
    # search, "brave" the Brave Search API with COALITIONKIT_BRAVE_API_KEY.
    search_provider: SearchProviderName = "off"
    search_model: str = "muse-spark-1.3"
    search_max_calls: int = 2
    search_max_results: int = 5

    # Reasoning models spend completion tokens on thinking: the budget covers thinking
    # plus the answer. Roles on Ollama (vault) send no effort.
    reasoning_effort: dict[Role, Effort] = _default_efforts()
    completion_budget: dict[Role, int] = _default_budgets()
    vault_model: str = "muse-glimmer"

    request_timeout_s: float = 60.0
    max_attempts: int = 4
    rate_limit_per_minute: dict[Role, int] = _default_limits()

    @property
    def steward_host(self) -> StewardProvider:
        """The explicit provider, else Baseten; missing keys fail closed at use."""
        if self.steward_provider is not None:
            return self.steward_provider
        return "baseten"

    @property
    def production(self) -> bool:
        return self.env == "production"

    @model_validator(mode="after")
    def _fail_closed_in_production(self) -> Self:
        if self.max_attempts < 1:
            raise SettingsError("COALITIONKIT_MAX_ATTEMPTS must be at least 1")
        if not 1 <= self.search_max_calls <= 5 or not 1 <= self.search_max_results <= 10:
            raise SettingsError(
                "COALITIONKIT_SEARCH_MAX_CALLS must be 1 to 5 and "
                "COALITIONKIT_SEARCH_MAX_RESULTS 1 to 10"
            )
        if min(self.completion_budget.values(), default=1) < 1:
            raise SettingsError("COALITIONKIT_COMPLETION_BUDGET must be positive")
        if not self.production:
            return self
        needed = ["meta_api_key"]
        if self.steward_host == "baseten":
            needed.append("baseten_api_key")
        missing = [
            f"COALITIONKIT_{name.upper()}" for name in needed if not _present(getattr(self, name))
        ]
        if missing:
            raise MissingKeyError("production needs " + ", ".join(missing))
        insecure = [
            f"COALITIONKIT_{name.upper()}"
            for name in ("meta_base_url", "baseten_base_url")
            if not getattr(self, name).startswith("https://")
        ]
        if insecure:
            raise SettingsError("production needs https for " + ", ".join(insecure))
        return self

    def route(self, role: Role) -> Route:
        """The model, endpoint and key name for a role."""
        match role:
            case "gardener":
                return Route(role, self.gardener_model, self.meta_base_url, "meta")
            case "composer":
                return Route(role, self.composer_model, self.meta_base_url, "meta")
            case "hosted_agent":
                return Route(role, self.hosted_agent_model, self.meta_base_url, "meta")
            case "steward":
                if self.steward_host == "baseten":
                    return Route(role, self.steward_baseten_model, self.baseten_base_url, "baseten")
                return Route(role, self.steward_model, self.meta_base_url, "meta")
            case "vault":
                return Route(role, self.vault_model, self.ollama_base_url, "ollama")

    def media_route(self, model: str) -> Route:
        """Media calls (images, SAM, transcription) always use the Meta endpoint and key."""
        return Route("composer", model, self.meta_base_url, "meta")

    def api_key(self, route: Route) -> str:
        """The key for a route. Raises MissingKeyError (naming the variable) when unset."""
        if route.key_name == "ollama":
            return LOCAL_PLACEHOLDER_KEY
        secret = self.meta_api_key if route.key_name == "meta" else self.baseten_api_key
        if secret is None or not _present(secret):
            raise MissingKeyError(f"COALITIONKIT_{route.key_name.upper()}_API_KEY is not set")
        return secret.get_secret_value()


def _present(secret: SecretStr | None) -> bool:
    return secret is not None and secret.get_secret_value().strip() != ""


def load_settings() -> Settings:
    """Read settings from the environment. Errors name variables and never echo values."""
    try:
        return Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})
        raise SettingsError("invalid settings: " + ", ".join(fields)) from None
