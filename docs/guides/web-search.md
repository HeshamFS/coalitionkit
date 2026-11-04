# Web search for agents

Agents in a room can search the web and cite what they found. Search is off by default. When it is on, a hosted agent looks up real places for a `place` need, and a `list` or `draft` maker searches when its need asks for something from outside the room. An agent you bring over MCP searches through the host with the `web_search` tool. Every search shows on the Table, and every result lists its sources.

## Turn it on

Set one variable on the host and restart it:

```sh
COALITIONKIT_SEARCH_PROVIDER=meta uv run coalitionkit up
```

| Provider | What it uses | Key | Cost |
|---|---|---|---|
| `off` | No search. Agents suggest kinds of place, not named ones | none | none |
| `meta` | The Meta endpoint's built-in `web_search` tool, through its Responses API | `COALITIONKIT_META_API_KEY` | metered tokens of `COALITIONKIT_SEARCH_MODEL` |
| `ddg` | DuckDuckGo through the `ddgs` package | none | none |
| `brave` | The Brave Search API | `COALITIONKIT_BRAVE_API_KEY` | your Brave plan |

`COALITIONKIT_SEARCH_MAX_CALLS` caps how many searches the Meta tool may run for one query (1 to 5, default 2). `COALITIONKIT_SEARCH_MAX_RESULTS` caps the pages kept (1 to 10, default 5).

The Meta provider costs about one cent per search with `muse-spark-1.3`, and takes 10 to 20 seconds. Its cost appears in the room's cost meter like any model call. The Meta chat completions endpoint refuses built-in tools, so this provider calls `/v1/responses` instead.

## What leaves the host

A hosted agent's query is built by code from public words only: the need's title and detail, and the goal. Nothing a person told their agent goes into it.

Every query is screened on the host before it is sent, whoever wrote it:

- The Steward's deterministic core policies run on it as if it were a message to the whole room. A phone number or an email address stops it.
- A street address stops it.
- Any private value a seat holds stops it: a free-text answer to a brief question, or something said privately to an agent.

A stopped query sends nothing. The Table shows "Search refused" with the reason, and an outside agent gets the error `steward_blocked`. The Meta tool may rephrase a query, so the queries it actually ran are screened again when the answer comes back, and their hits are dropped if one fails.

## What comes back

A hit is a title, a URL and a snippet. Only `http` and `https` URLs count. With the Meta provider, the model describes the pages, but a page counts only if the search itself returned its URL. A model cannot invent a source.

A `place` result then names two or three real places from those pages, each with why it fits, what to check first and its URL. The maker must copy each URL from the hits, and code drops any place whose URL is not among them. The place carries `provenance: "search"`.

The pages stay with the result in `data.web`. The result dialog lists them under **Found on the web**, and **Show the work** adds the queries that found them. Links open in a new tab with no referrer.

Search is reused: when the hosted agents offer on a `place` need, the first one looks it up and tells its own person what it found. The maker of the result reuses those pages instead of searching again.

## From an outside agent

An agent connected over MCP calls:

```json
{"tool": "web_search", "arguments": {"coalition_id": "<id>", "query": "quiet cafe for a board game evening"}}
```

It gets `{coalition_id, query, results: [{title, url, snippet}]}`. The query must be 1 to 200 characters. The same screen applies, and the search shows on the Table with the agent's seat.

## What search does not do

Search finds pages; it does not check them. A page can be out of date, and a place can be closed or full. That is why each place says what to check first. The Steward checks policy, not truth.
