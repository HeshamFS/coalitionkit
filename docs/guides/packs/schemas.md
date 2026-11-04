# Schemas and private fields

A pack adds fields to needs and offers, only inside their `ext` object. The core schema checks the payload, then the pack's schema checks `ext`. A failure is `schema_invalid`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "tool-library tool on offer",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "tool_kind": { "enum": ["ladder", "drill", "saw", "paint-sprayer", "other"] },
    "condition": { "enum": ["new", "good", "worn"] },
    "pickup_note": { "type": "string", "maxLength": 200 },
    "shed_key_code": { "type": "string", "x-private": true },
    "home_address": { "type": "string", "x-private": true }
  }
}
```

## Private fields

Mark a field `"x-private": true` and it belongs in the member's vault. It must not be sent in a transmitted `ext`, and a viewer's feed gets the schema without it.

Marking a field private does not stop someone from typing the same thing in a free-text field. Keep free text short, and add a [policy](policies.md) for what must never appear.

Without a bound pack, `ext` must be absent.

To compare private sets such as colours or tools people own without anyone showing their list, see [Compared sets](compare.md).
