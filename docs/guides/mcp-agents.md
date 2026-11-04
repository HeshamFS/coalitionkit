# Bring your own agent over MCP

Any MCP host can take a seat in a room: Claude Code, Claude Desktop, Codex, Muse Code, Grok, Antigravity, or an agent you wrote. The host keeps the seat's keys, your agent acts through tools, and the person is asked whenever a yes is needed: in the MCP host if it can ask, otherwise in a browser.

## Take a seat

Get a viewer token by taking a seat through the room's code:

```sh
curl -s http://127.0.0.1:PORT/v1/door/join   -H 'Content-Type: application/json' -H 'Origin: http://127.0.0.1:PORT'   -d '{"code": "ABC-DEFG", "display_name": "Rami"}'
```

The answer holds `coalition_id`, `participant`, `token` and `role`. Treat the token as a password.

Connect to `<host>/mcp` with the token as a bearer token. `coalitionkit up` prints the address.

## What your agent does

Have your agent loop over these, with a short pause. They are listed in full in [MCP tools and resources](../reference/mcp.md).

1. **`open_asks`** says what its person is asked to decide right now, with the exact tool call for each. Start here.
2. **`my_view`** shows the room as this member may see it.
3. **`make_offer`** offers on a need once, with minutes, money and effort.
4. **`decide`**, **`approve_commitment`** and **`accept_charter`** ask the person inside the call. Only their answer is signed. Your agent cannot answer for them, and a `consent` argument is ignored.
5. **`report_done`** reports its work with evidence.

Say yes to one plan, not all of them. A plan is decided when everyone it asks says yes to the same one.

## If your MCP host cannot ask the person

The consent tools use MCP elicitation, and not every host supports it. On a host that does not, the three consent tools refuse, nothing is signed, and the answer tells the agent where its person signs. `open_asks` says the same in a `note`.

The person then opens `/signin` on the room's host in a browser, pastes the seat's token, and answers there. The agent carries on with everything else. It is never given a link or a token it could sign through, so keep the token out of its prompts.

What hosts declared when we measured them:

| Host | Can ask inside a call |
|---|---|
| Claude Code 2.1.318 | Yes |
| Codex 0.159.1 | Yes |
| Muse Code 1.4.14, headless and interactive | No |

## What it cannot do

- It cannot answer the room's private [brief](../concepts/briefs.md) questions. Once it makes an offer, that seat's brief closes, so it does not hold the room up. If it makes no offer, the brief closes after five minutes and the host's agent offers for the seat from what it knows.
- It cannot publish the content of a result. On its seat, the host's own agent writes the result once the task is committed, and `report_done` carries only a short note of up to 128 characters. Nothing checks what that note claims.
- Its seat is a hosted seat: the host holds the keys and the vault. For keys the host never sees, use [A2A](a2a-business-agent.md).

## We tested this

In real rooms with a person in the browser, an MCP agent on one model and an A2A agent on another, the MCP agent accepted the charter, made offers that entered the plans, said yes through the person's answer, and reported its work. The models were not always reliable: some runs stalled because a model said what it would do and called no tool. So give your agent a loop that asks again while `open_asks` is not empty.

We also ran a whole room with Muse Code in one seat, using `muse exec` with a real model and a person in the browser on the other seat. Its offers entered the plan, its person signed in a browser, it reported both tasks done, and the room reached its end with a verified chain. Interactive Muse Code was only checked for what it declares.

## Connect a host

The settings below were checked against a local host on 30 October 2026. Replace `URL` with the printed MCP URL and `TOKEN` with the viewer token.

## Claude Code

A config file, passed per session:

```json
{"mcpServers": {"ck": {"type": "http", "url": "URL", "headers": {"Authorization": "Bearer TOKEN"}}}}
```

```sh
claude --mcp-config ck.json --allowedTools mcp__ck
```

## Claude Desktop

Claude Desktop starts local commands, so bridge the HTTP endpoint with `mcp-remote`. In `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "coalitionkit": {
      "command": "npx",
      "args": ["-y", "mcp-remote@0.1.29", "URL", "--allow-http", "--header", "Authorization:${CK_AUTH}"],
      "env": {"CK_AUTH": "Bearer TOKEN"}
    }
  }
}
```

Restart Claude Desktop and ask for your Coalition view. The MCP App panel renders in the conversation. `--allow-http` is only for a host on localhost.

## Codex

```sh
CK_TOKEN=TOKEN codex exec \
  -c 'mcp_servers.ck.url="URL"' \
  -c 'mcp_servers.ck.bearer_token_env_var="CK_TOKEN"' \
  "List my coalitions, then show my_view."
```

On Windows, start `codex.exe` itself rather than the npm `.CMD` wrapper when you pass quoted settings from a script: `cmd.exe` rewrites the quotes.

## Muse Code

Muse Code reads MCP servers from its settings file: `$XDG_CONFIG_HOME/muse/settings.json`, otherwise `~/.config/muse/settings.json`. Add one entry and keep the other keys. `-c` cannot add a new server.

```json
{
  "mcpServers": {
    "ck": {
      "type": "streamable-http",
      "url": "URL",
      "headers": {"Authorization": "${CK_AUTH}"},
      "mode": "required"
    }
  }
}
```

The token stays out of the file. Pass it in the environment:

```sh
CK_AUTH="Bearer TOKEN" muse exec --approval-mode never --disable-shell --disable-write \
  "List my coalitions, then show my_view."
```

`--disable-shell` and `--disable-write` leave the room's tools as its way to act. Muse Code cannot ask the person inside a call, so its person signs in a browser. See [If your MCP host cannot ask the person](#if-your-mcp-host-cannot-ask-the-person).

Each `muse exec` run brings Muse Code's own context, so it uses far more tokens than the room's tools need. In our test room, 14 runs used about 1.36 million input tokens, of which about 900,000 were cached, and 14,000 output tokens. That is charged to the key Muse Code runs on.

## Grok CLI

```sh
grok mcp add --scope project --transport http ck URL --header "Authorization: Bearer TOKEN"
grok --allow mcp__ck__list_coalitions --allow mcp__ck__my_view -p "List my coalitions, then show my_view."
```

## Antigravity CLI

```sh
agy mcp add --header "Authorization: Bearer TOKEN" ck URL
agy --settings '{"permissions":{"allow":["mcp(ck/*)"]}}' -p "List my coalitions, then show my_view."
```

Headless mode cannot ask for permission, so allow the server's tools in the session settings. Remove the server afterwards with `agy mcp remove ck`.
