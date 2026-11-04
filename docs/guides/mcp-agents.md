# Connect an MCP host

Every member reaches its Coalition through the host's MCP endpoint, `<host>/mcp`, with its own viewer token as a bearer token. Each host sees only that member's scope. Start a local host with `uv run coalitionkit up`; it prints the MCP URL and one viewer token per demo member.

The tools a member gets: `list_coalitions`, `my_view`, `open_asks`, `pending_questions`, `join_coalition`, `answer_question`, `make_offer`, `commit`, `report_ripple`, `report_done`, `leave_coalition`, and for consent `decide`, `approve_commitment` and `accept_charter`. `my_view` returns the member's surface as data, as readable text, and with a link to the MCP App view `ui://coalitionkit/surface-v1.html` for hosts that render MCP Apps.

The settings below were checked on 30 October 2026 against a local host. Replace `URL` with the printed MCP URL and `TOKEN` with a viewer token.

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
