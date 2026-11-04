# Policies

A pack's policies are checked by fixed rules, after the core checks and before the Steward's model audit.

```yaml
id: tool-no-payment-details
applies_to: [coalition.observe, coalition.offer]
when:
  any_text_matches:
    - '\biban\b'
    - '\b[a-z]{2}\d{2}(?:\s?[a-z0-9]{4}){3,7}\b'
then: block
explain: "Loans are free. Leave bank details out of the room."
```

## What a policy can do

| `then` | Effect |
|---|---|
| `allow` | Let it through |
| `redact` | Hide each field the policy matched from everyone but the host and the Steward |
| `block` | Refuse it as `pack_violation`, with the policy's id |
| `escalate` | Hold it. It does not count, the sender is told, and their person may revise and resend it |

If several policies match, the most severe action wins.

`quarantine` acts on a participant rather than a message, so it stays with the core. The loader refuses a pack that declares it.

Write `explain` for the person who gets stopped: it is what they read.

## Test it

Add a scenario to your [evals](evals-and-acceptance.md) that tries the thing the policy forbids, with a canary value. An eval fails if a canary reaches anyone it should not.

Text matching is not understanding. A policy like this stops a pattern, not every way of saying something, and the Steward's model audit is the second check.
