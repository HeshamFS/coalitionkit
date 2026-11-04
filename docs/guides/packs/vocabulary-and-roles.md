# Vocabulary and roles

## Roles

Roles say who may do what. A member's message needs an ability its role grants, or it is refused as `not_authorized`.

| Ability | Lets a member |
|---|---|
| `charter` | Approve the charter |
| `offer` | Make offers |
| `decide` | Decide on plans for the whole room |
| `decide_own` | Decide only about their own part |
| `commit` | Commit to tasks |

```yaml
roles:
  keeper: { label: Keeper, may: [charter, offer, decide, commit] }
  shed: { label: Tool shed, may: [offer] }
```

## Vocabulary

Vocabulary changes the words on screen for core objects. It goes to each viewer's screen, and is never part of a signed payload.

```yaml
task: loan
resource: tool
need: tool request
offer: { one: tool on offer, other: tools on offer }
commitment: loan promise
```

## Views

`views.yaml` sets the order of components per role and device, and can add components of the pack's own:

```yaml
components:
  ShedNote:
    props: [title, body]
    required: [title]
order:
  keeper:
    wide: [Card, ShedNote, Text]
    compact: [Text, Card]
    message: [Text]
```

A pack cannot reference a component outside the core catalog or its own.
