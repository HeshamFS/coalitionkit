# Environment and settings

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

Every setting comes from an environment variable with the prefix `COALITIONKIT_`. Secrets never appear in logs, errors or `repr`.

`coalitionkit up` sets its own host settings and reads only the model keys below. `coalitionkit server serve` reads all of them.

## Host

| Variable | Type | Default |
|---|---|---|
| `COALITIONKIT_STORE` | `SecretStr` | `none (secret)` |
| `COALITIONKIT_HOST_KEY_FILE` | `pathlib.Path` | `set at start` |
| `COALITIONKIT_PUBLIC_BASE_URL` | `str` | `http://127.0.0.1:8000` |
| `COALITIONKIT_BIND_HOST` | `str` | `127.0.0.1` |
| `COALITIONKIT_BIND_PORT` | `int` | `8000` |
| `COALITIONKIT_SURFACES` | `set[Literal['mcp', 'feed', 'agent']]` | `['agent', 'feed', 'mcp']` |
| `COALITIONKIT_PACKS` | `list[pathlib.Path]` | `set at start` |
| `COALITIONKIT_PACK_TRUSTED_KEYS` | `dict[str, dict[str, str]]` | `set at start` |
| `COALITIONKIT_GENESIS` | `Literal['off', 'local', 'admin']` | `off` |
| `COALITIONKIT_ROOM_ENGINE` | `Literal['on', 'off']` | `off` |
| `COALITIONKIT_ROOM_TALK_ROUNDS` | `int` | `2` |
| `COALITIONKIT_ROOM_TALK_WAIT_S` | `float` | `45.0` |
| `COALITIONKIT_ROOM_BUDGET_USD` | `float \| None` | `none` |
| `COALITIONKIT_ROOMS_PER_DAY` | `int \| None` | `none` |
| `COALITIONKIT_STANDING_ROOM_GOAL` | `str \| None` | `none` |
| `COALITIONKIT_STANDING_ROOM_PACK` | `str \| None` | `none` |
| `COALITIONKIT_STANDING_ROOM_MINUTES` | `float` | `15.0` |
| `COALITIONKIT_STANDING_ROOM_GATHER_MINUTES` | `float` | `5.0` |
| `COALITIONKIT_STANDING_ROOM_SEATS` | `int` | `12` |
| `COALITIONKIT_SAMPLE_ROOMS` | `pathlib.Path \| None` | `none` |
| `COALITIONKIT_ADMIN_TOKEN` | `SecretStr \| None` | `none (secret)` |
| `COALITIONKIT_WHATSAPP_TOKEN` | `SecretStr \| None` | `none (secret)` |
| `COALITIONKIT_WHATSAPP_PHONE_NUMBER_ID` | `str \| None` | `none` |
| `COALITIONKIT_WHATSAPP_APP_SECRET` | `SecretStr \| None` | `none (secret)` |
| `COALITIONKIT_WHATSAPP_VERIFY_TOKEN` | `SecretStr \| None` | `none (secret)` |
| `COALITIONKIT_CONFIRM_LINK_BASE` | `str \| None` | `none` |
| `COALITIONKIT_CATALOG_FILE` | `pathlib.Path` | `spec/catalog/coalitionkit-v0_9.json` |

## Models

| Variable | Type | Default |
|---|---|---|
| `COALITIONKIT_ENV` | `Literal['development', 'test', 'production']` | `development` |
| `COALITIONKIT_META_API_KEY` | `SecretStr \| None` | `none (secret)` |
| `COALITIONKIT_BASETEN_API_KEY` | `SecretStr \| None` | `none (secret)` |
| `COALITIONKIT_BRAVE_API_KEY` | `SecretStr \| None` | `none (secret)` |
| `COALITIONKIT_META_BASE_URL` | `str` | `https://api.meta.ai/v1` |
| `COALITIONKIT_BASETEN_BASE_URL` | `str` | `https://inference.baseten.co/v1` |
| `COALITIONKIT_OLLAMA_BASE_URL` | `str` | `http://localhost:11434/v1` |
| `COALITIONKIT_GARDENER_MODEL` | `str` | `muse-wonder-1.0` |
| `COALITIONKIT_COMPOSER_MODEL` | `str` | `muse-spark-1.3` |
| `COALITIONKIT_HOSTED_AGENT_MODEL` | `str` | `muse-spark-1.3` |
| `COALITIONKIT_STEWARD_MODEL` | `str` | `muse-spark-1.3` |
| `COALITIONKIT_STEWARD_PROVIDER` | `Optional[Literal['meta', 'baseten']]` | `none` |
| `COALITIONKIT_STEWARD_BASETEN_MODEL` | `str` | `meta-models/muse-spark-open` |
| `COALITIONKIT_IMAGE_MODEL` | `str` | `muse-image-1.0` |
| `COALITIONKIT_SEGMENT_MODEL` | `str` | `sam-3.1` |
| `COALITIONKIT_TRANSCRIBE_MODEL` | `str` | `muse-voice-transcribe-1.0` |
| `COALITIONKIT_MEDIA_RATE_LIMIT_PER_MINUTE` | `int` | `120` |
| `COALITIONKIT_SEARCH_PROVIDER` | `Literal['off', 'meta', 'ddg', 'brave']` | `off` |
| `COALITIONKIT_SEARCH_MODEL` | `str` | `muse-spark-1.3` |
| `COALITIONKIT_SEARCH_MAX_CALLS` | `int` | `2` |
| `COALITIONKIT_SEARCH_MAX_RESULTS` | `int` | `5` |
| `COALITIONKIT_REASONING_EFFORT` | `dict[Literal['gardener', 'composer', 'hosted_agent', 'steward', 'vault'], Literal['minimal', 'low', 'medium', 'high']]` | `{'hosted_agent': 'minimal', 'composer': 'low', 'gardener': 'low', 'steward': 'low'}` |
| `COALITIONKIT_COMPLETION_BUDGET` | `dict[Literal['gardener', 'composer', 'hosted_agent', 'steward', 'vault'], int]` | `{'gardener': 4000, 'composer': 4000, 'hosted_agent': 4000, 'steward': 4000, 'vault': 4000}` |
| `COALITIONKIT_VAULT_MODEL` | `str` | `muse-glimmer` |
| `COALITIONKIT_REQUEST_TIMEOUT_S` | `float` | `60.0` |
| `COALITIONKIT_MAX_ATTEMPTS` | `int` | `4` |
| `COALITIONKIT_RATE_LIMIT_PER_MINUTE` | `dict[Literal['gardener', 'composer', 'hosted_agent', 'steward', 'vault'], int]` | `{'gardener': 30, 'composer': 60, 'hosted_agent': 120, 'steward': 120, 'vault': 600}` |
