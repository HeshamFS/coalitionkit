# Write a Discipline Pack

A **Discipline Pack** teaches the room a field of work: its words, its roles, what a need looks like, what must never be said, and how to allocate fairly. A pack is a folder of data. The core kit holds no field-specific knowledge, so this is where it goes.

A pack cannot run code in the host. It is checked by a strict loader, and a pack that breaks a rule does not load.

## The commands

```sh
coalitionkit pack validate my-pack      # check every rule
coalitionkit pack eval my-pack          # run its scripted scenarios
coalitionkit pack accept my-pack        # run its whole journey, from the start of a room to its end
coalitionkit pack sign my-pack --key key.pem --kid me
coalitionkit up --pack my-pack          # install it on a local host
```

`eval` and `accept` take `--live` to use real models. Exit 0 means it passed, 1 means it failed, and 2 means bad usage.

## The pages

1. [A complete small pack](example.md): start by copying one.
2. [Vocabulary and roles](vocabulary-and-roles.md)
3. [Schemas and private fields](schemas.md)
4. [Templates and allocation](templates-and-allocation.md)
5. [Policies](policies.md)
6. [Mint templates and connectors](mint-and-connectors.md)
7. [Skills and lessons](skills-and-lessons.md)
8. [Evals and acceptance](evals-and-acceptance.md)

The full list of keys is in [Pack format](../../reference/pack-format.md).

## Packs in the repository

[`packs/`](https://github.com/HeshamFS/coalitionkit/tree/main/packs) has four examples: `daily-life`, `science-lab`, `supper-club` (friends cooking one dinner from their own kitchens, with a private diet compared by PSI) and `travel-disruption`. [`examples/packs/tool-library`](https://github.com/HeshamFS/coalitionkit/tree/main/examples/packs/tool-library) is the small one these pages use.
