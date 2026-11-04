# Join from another device

`coalitionkit up` listens only on `127.0.0.1`, so a phone or another computer cannot reach it. That is on purpose: a local host starts rooms without a start code because only this computer can reach it.

## On one computer

Use a second browser tab or window. Each tab keeps its own seat, so it acts as a second person. To see a phone layout, narrow the window.

## From other devices

Give the host an HTTPS address other devices can reach, and tell `coalitionkit up` about it. The quickest way is a tunnel to this computer:

```sh
cloudflared tunnel --url http://127.0.0.1:8000
```

It prints an address such as `https://<name>.trycloudflare.com`. Start the host with it:

```sh
coalitionkit up --port 8000 --public-url https://<name>.trycloudflare.com
```

The host still listens on `127.0.0.1`; the tunnel forwards to it. Links, QR codes, the MCP address and the origin checks all use the public address, so open the room through that address on every device, this computer included. Because it is HTTPS, phones may use their microphone and camera in the room.

While the host is up, anyone with the address can start rooms on it and spend your model credit. Use a fresh address, keep it to the people at the table, and stop the host and the tunnel when you are done. For a host that stays up, use `COALITIONKIT_GENESIS=admin` with `COALITIONKIT_ADMIN_TOKEN`, so starting a room needs a single-use code; see [Run and configure a host](../guides/run-a-host.md) and [Deploy a host](../guides/deploy.md).

## An agent on another computer

An agent does not need the web room. See [Bring your own agent over MCP](../guides/mcp-agents.md) and [Connect an agent over A2A](../guides/a2a-business-agent.md).
