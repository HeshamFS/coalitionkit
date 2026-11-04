# Troubleshooting

When `coalitionkit up` cannot start, it prints `Could not start:` and the reason.

| You see | Do this |
|---|---|
| `the web room is not built and npm was not found` | From a clone, install Node 22 or newer, or start with `--no-web`. |
| `` `npm run build` failed `` | The output above it says why. Try `npm --prefix apps/web ci`, then run `up` again. |
| `this install has no web room files` | Reinstall `coalitionkit`, or start with `--no-web`. |
| `stored host requires the original port` | Run without `--port`, or use a new `--data-dir`. A host's address is part of its identity. |
| An address already in use | Choose another `--port` with a new `--data-dir`, or stop the other host. |
| `Private set intersection requires ...` | Install `coalitionkit[psi]` and the libsodium library. See [Install](install.md). |

## In the room

**It says no model is set up.** The host did not see `COALITIONKIT_META_API_KEY` in its environment. See [Model keys](model-keys.md).

**The Steward held the plans.** The room says so, and no plan is sent until something changes. Say what should change, in the box at the bottom.

**Every plan was turned down.** Say what would change, or have someone make a better offer. New plans come from new offers.

**Everyone said yes to different plans.** A plan needs a yes from every person it asks. If the plans have a real trade-off, the room asks everyone to vote. Otherwise someone has to choose another plan.

**A seat stays on "briefing".** That person has not answered their questions. The brief closes by itself after five minutes, and the room goes on.

**I went back to the first page and see a sign-in form.** The tab still holds a token from an ended room. Open a new tab.

## Starting over

`coalitionkit up --reset` removes the data folder it made and starts a new host. It refuses a folder it did not create. State lives in `./.coalitionkit` unless you choose another `--data-dir`.
