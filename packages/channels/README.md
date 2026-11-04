# CoalitionKit channels

Transports for the message door, so a person can take part without opening a browser. The core names none of them. Each lives in its own subpackage.

`coalitionkit_channels.whatsapp` is the WhatsApp Cloud API transport: a webhook that checks Meta's signature, single-use codes that bind a thread to a seat, a send limit, and log redaction. A decision that needs a signature sends a link to a confirm page, because a message cannot carry a press and hold.

See the [WhatsApp guide](https://github.com/HeshamFS/coalitionkit/blob/main/docs/guides/whatsapp.md).

Part of [CoalitionKit](https://github.com/HeshamFS/coalitionkit).
