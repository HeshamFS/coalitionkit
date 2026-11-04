# The Mint

The **Mint** turns a short video and a voice note about a shared resource or device into a running MCP server, with its rules enforced. For example, it can make a booking server for something people take turns using.

## What keeps it safe

- **Models fill in templates. They write no code.** They return bounded JSON that fills reviewed Python templates: `resource` and `device`. A [pack](packs/mint-and-connectors.md) can add its own with their own tests.
- **Rules live in the database.** Durations and occupancy limits are enforced inside SQLite write transactions.
- **It must survive attacks before it can publish.** `mint` returns a running server only after every MCP attack passes.
- **A person approves it.** Before approval, MCP calls from outside the proof runner are refused. Approval is a signature from the owner's key, never a true or false argument.
- **Holds need the owner too.** Confirming and cancelling always require owner signatures, and each signed proof can be used once.

## Use it

`coalitionkit_mint.pipeline.mint` takes local video and WAV paths, a destination, the owner's public key, a metered `ModelGateway` and a `MediaClient`. It returns a running `Minted` handle. Call `close()` in a `finally` block to stop the child process.

Sign `artifact.consent_payload(hash, "approve", {})` with `coalitionkit_contracts.signing.sign_detached`, then pass the result and the owner key to `Minted.approve(signature, owner_key)`.

The package's [README](https://github.com/HeshamFS/coalitionkit/blob/main/packages/mint/README.md) has the details of holds and proofs.

## In a room

A seated person can mint a device from inside a room. On the Table, open **Bring a device** under *Devices at the table*, then give it a name, say what it is, pick the need it serves, and attach the video and the voice note. The host runs the Mint in the background, and everyone sees its stages.

1. **Mint.** `POST /v1/room/mint` takes the video, the WAV and an optional template: `resource` for something people take turns using, `device` for a display with readings, or a template from the room's [pack](packs/mint-and-connectors.md). The uploads are removed when the pipeline ends.
2. **Approve.** When every attack is refused, the device waits for its owner. Their press-and-hold calls `POST /v1/room/mint/approve`, and the host signs `consent_payload(hash, "approve", {})` with that person's own owner key. Nobody else can approve it.
3. **Seat.** The host seats the device through a one-use invitation, as it seats a helper. Its card shows on the ring with a *device* tag, and the owner's signed card stays with the artifact.
4. **Offer and confirm.** A resource offers on the needs it serves, each offer standing on a hold it has already taken. When the plan gives it the need and its commitment is approved, the host confirms the hold with the owner's signature, once. The owner's yes on that plan is the consent. The device then publishes the booking as its result and reports done.
5. **Read and ripple.** The owner points a phone at a display and sends a frame with `POST /v1/room/mint/frame`. The device reads it with the same SAM and vision steps as the Mint, publishes the reading as an `observe` with source `device`, and sends a ripple on the needs that name it when a reading crosses its threshold.

A device serves the needs you pick. If you pick none, it serves the needs whose title or detail shares a word of four letters or more with its name.

Each minted tool call is reported as an activity with tool `mint:<tool>`. Its arguments are a time window at most, never a nonce or a signature.

The minted processes live in the host's memory. If the host restarts, its devices show as offline until they are minted again.

!!! note
    A live run calls the Meta media models and spends credit. A mint in a room took 50 to 71 seconds and cost 4 to 5 US cents in the runs we measured.
