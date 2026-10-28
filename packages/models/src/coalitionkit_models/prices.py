# SPDX-License-Identifier: Apache-2.0
"""The versioned price table. Money is integer micro-USD per 1,000,000 tokens."""

from __future__ import annotations

import json
from importlib import resources
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from .errors import UnpricedModelError

MTOK = 1_000_000
MicroUsd = Annotated[int, Field(ge=0)]


class ModelPrice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input: MicroUsd = 0
    output: MicroUsd = 0
    cached_input: MicroUsd = 0
    per_image: MicroUsd = 0
    per_audio_hour: MicroUsd = 0
    source: str
    verified: bool


class PriceTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    currency: str
    unit: str
    models: dict[str, ModelPrice]

    def price(self, model: str) -> ModelPrice:
        try:
            return self.models[model]
        except KeyError:
            raise UnpricedModelError(
                f"no price for model {model!r} in table {self.version}"
            ) from None

    def cost_micro_usd(
        self, model: str, *, prompt_tokens: int, completion_tokens: int, cached_tokens: int = 0
    ) -> int:
        """Cost of one response in micro-USD, rounded up once over the whole response.

        ``prompt_tokens`` includes the cached tokens, as in the OpenAI usage object.
        """
        if min(prompt_tokens, completion_tokens, cached_tokens) < 0:
            raise ValueError("token counts cannot be negative")
        cached = min(cached_tokens, prompt_tokens)
        price = self.price(model)
        scaled = (
            (prompt_tokens - cached) * price.input
            + cached * price.cached_input
            + completion_tokens * price.output
        )
        return -(-scaled // MTOK)

    def media_cost_micro_usd(self, model: str, *, images: int = 0, audio_ms: int = 0) -> int:
        """Cost of a media call in micro-USD: per image, or per audio hour rounded up."""
        return _media_cost(self.price(model), images, audio_ms)


MS_PER_HOUR = 3_600_000


def _media_cost(price: ModelPrice, images: int, audio_ms: int) -> int:
    if min(images, audio_ms) < 0:
        raise ValueError("media units cannot be negative")
    return images * price.per_image + -(-(audio_ms * price.per_audio_hour) // MS_PER_HOUR)


def load_price_table(version: str | None = None) -> PriceTable:
    """Load a table from the package. Without ``version`` the newest file wins."""
    folder = resources.files("coalitionkit_models").joinpath("prices")
    names = sorted(p.name for p in folder.iterdir() if p.name.endswith(".json"))
    if not names:
        raise FileNotFoundError("no price tables bundled")
    wanted = f"{version}.json" if version else names[-1]
    if wanted not in names:
        raise FileNotFoundError(f"price table {wanted} not found; have {names}")
    table = PriceTable.model_validate(json.loads(folder.joinpath(wanted).read_text("utf-8")))
    if table.version != wanted.removesuffix(".json"):
        raise ValueError(f"price table {wanted} declares version {table.version}")
    return table
