# Plans and fairness

A **plan** says who takes each need. Fixed rules build plans from the offers. A model names and explains them but never builds them.

## How plans are built

The Gardener looks for assignments that cover every need and scores each on three things: total cost, how evenly the load falls, and how well the work matches what people prefer. It offers up to three plans that differ on these, so each is the best at something.

Live rooms often produce one to three plans. One plan is honest when the offers do not conflict.

## What you see

Every plan has a name and a line from the model, and says what it gives up, such as "takes 15 minutes longer in all, puts more on Member 2". Each person also gets a **for you only** line: what it means for them, drawing on what they told their agent. Nobody else sees that line.

## Deciding

A plan is decided when everyone it asks says yes to that same plan.

- **A real trade-off** raises a vote called a tension. Each person chooses one option. A split vote sends the work back to be planned again.
- **A no** sends the work back too. New plans come, and a plan refused on the same terms does not return. If an offer later improves, that assignment can be asked again.
- **Every plan refused:** the room says so, and waits for someone to say what would change.

!!! note "A known limit"
    When no vote is raised and people say yes to different plans, nothing moves until someone chooses another. The screen does not yet show who chose what.

## Fairness

The Steward's `fairness-cap-exceeded` policy limits how much of a plan one person may carry. The planner uses the same cap, so plans it would stop are held back when others exist. If no allocation fits, for example with too few people, the cap is dropped rather than leaving the room with nothing.

## Held plans

The Steward reviews each plan set. If a fixed policy objects, the room stops and says so. If the model audit objects, it reads the plans once more, because its verdict can differ between reads. A set that stays held is not sent again until the offers change.
