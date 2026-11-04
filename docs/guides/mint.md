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

!!! note
    A live run calls the Meta media models and spends credit. The Mint runs on its own. It is not yet part of the room's flow.
