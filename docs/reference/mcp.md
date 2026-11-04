# MCP tools and resources

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

A member reaches the host at `<host>/mcp` with its viewer token as a bearer token. Each member sees only its own view. To connect a host, see [Bring your own agent over MCP](../guides/mcp-agents.md).

## Read

| Tool | Arguments | What it does |
|---|---|---|
| `my_view` | `coalition_id`, `device` | Show this participant's live Coalition surface, as readable text with its data attached. |
| `list_coalitions` |  | List the Coalitions this participant belongs to. |
| `pending_questions` | `coalition_id` | List the open questions addressed to this participant's vault. |
| `open_asks` | `coalition_id` | List what this participant is asked to decide right now, with the tool call for each. |

## Act

| Tool | Arguments | What it does |
|---|---|---|
| `join_coalition` | `invite`, `roles` | Join a Coalition from an invitation link or Coalition ID, with the roles you ask for. |
| `answer_question` | `coalition_id`, `query_id`, `result` | Answer an open question from your vault: yes, no or a cost. |
| `make_offer` | `coalition_id`, `target`, `capacity`, `cost`, `valid_until` | Offer capacity against a need or task. Defaults to an offer valid for 24 hours. |
| `commit` | `coalition_id`, `task_id`, `status`, `commitment_id` | Create a commitment (status pending) or withdraw one (status withdrawn, with its ID). |
| `report_ripple` | `coalition_id`, `change`, `invalidates` | Report a change and the task IDs it invalidates. |
| `report_done` | `coalition_id`, `task_id`, `evidence` | Report an approved task done, with evidence. |
| `leave_coalition` | `coalition_id` | Leave the Coalition. Your open offers are withdrawn. |

## Ask the person

| Tool | Arguments | What it does |
|---|---|---|
| `decide` | `coalition_id`, `subject`, `choice`, `consent` | Record the person's decision on a subject at a revision. |
| `approve_commitment` | `coalition_id`, `commitment_id` | Approve a commitment at its current revision, after the person confirms it. |
| `accept_charter` | `coalition_id` | Accept the charter at its current revision, after the person confirms it. |

In the tools under **Ask the person**, the host asks the person inside the call. Only their answer is signed. No tool argument can stand in for it.

## Resources

| URI | What it holds |
|---|---|
| `coalition://{id}/charter` | The charter. |
| `coalition://{id}/my-tasks` | This member's tasks. |
| `coalition://{id}/log{?since}` | The log, as this member may see it. |
