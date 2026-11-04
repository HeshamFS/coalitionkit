# The Steward

The **Steward** is an independent checker that reviews messages before they reach anyone. It never acts for a member, and it holds no vault.

## Two steps

1. **Fixed policies** run first. They always run, and no model can skip them.
2. **A model audit** then reads the message as each recipient would see it. By default it runs on a different model and provider from the agents, so one model's blind spot is less likely to pass both.

The model audit is a judgement call and can differ between reads. A plan set it holds gets one more read before the room stops. A fixed policy stops it at once.

## The fixed policies

| Policy | What it holds |
|---|---|
| `no-contact-details-in-room` | Phone numbers and email addresses are not shared with the whole room |
| `no-private-field-in-outbound` | Private fields are removed before a message reaches anyone else |
| `no-contact-before-consent` | Nobody is contacted until they have consented to it |
| `no-regulated-advice` | Coordinate the task; leave the advice to a qualified person |
| `fairness-cap-exceeded` | One person would carry more than 60 percent of the work in a plan |

A [Discipline Pack](../guides/packs/policies.md) can add its own.

## What a verdict does

| Verdict | Effect |
|---|---|
| Allow | The message goes through |
| Redact | Named fields are removed for that recipient |
| Block, quarantine | The message is held. It is not sent |
| Escalate | The message is held for a person. The model's rule is to answer this when unsure |

Verdicts are signed. If the audit cannot run, for example if the model is down, the Steward does not pass messages it could not check. The room shows this as a hold.

## What you see

A stopped message shows as **Stopped by the Steward** on the sender's side, with a badge on their seat. The people it was aimed at never see it. The events-checked count at the top of the room counts everything reviewed, including what was stopped.

## What it does not do

The Steward checks policy, not truth. It will not notice that a venue an agent named does not exist. See [Security](../security/threat-model.md) for the limits.
