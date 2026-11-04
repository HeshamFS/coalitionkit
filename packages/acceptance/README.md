# CoalitionKit acceptance

Harnesses that run a whole coalition and measure what happened: interop over the A2A wire, privacy with planted canaries, ripple, scale, chaos and cost. It also runs a Discipline Pack's evals and its [acceptance journey](https://github.com/HeshamFS/coalitionkit/blob/main/docs/guides/packs/evals-and-acceptance.md).

Tests that spend money or need a service are marked `live`, and run only with `COALITIONKIT_LIVE=1` and a key. Without those they are reported as not run, never as passed.

Part of [CoalitionKit](https://github.com/HeshamFS/coalitionkit).
