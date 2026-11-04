# Skills and lessons

## Skills

A skill is a `SKILL.md` that tells an agent how to act in this field. Every agent that joins is offered the pack's skills, through the MCP resource `coalition://{id}/skills` and the join reply.

```markdown
# Lend a tool

Join with the role you were given: a keeper approves the charter and the plan, a lender
offers and commits, a tool shed can only offer.
Offer only a tool you own and can hand over in the requested window.
Never put the shed key code or a home address in an offer. They stay in your vault.
Keep a commitment pending until your person signs it. An agent yes cannot replace consent.
```

## Lessons

A lesson template is filled in from the log when the room ends, and is kept as a skill for next time. See [Lessons as skills](../../concepts/lessons-as-skills.md).

```markdown
# Lesson: who lent what

Goal: {{goal}}
Members: {{members}}
Requests: {{tasks}}
Allocation: {{allocation}}
Changes during the run: {{changes}}
Duration: {{duration}}

Next time: ask for the most-wanted tools first.
```

Placeholders come from a fixed set: `goal`, `members`, `tasks`, `allocation`, `decisions`, `changes`, `policy_outcomes` and `duration`.
