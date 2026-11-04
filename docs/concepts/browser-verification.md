# Browser verification

You do not have to trust the host's word for the record. **Check the record myself** has your browser verify it, with its own cryptography and no call to the host.

## What it checks

- Each entry's hash matches its content.
- Each entry links to the one before it, from the room's first entry onward.
- Each signature you can see is valid for the key that claims it.
- The newest receipt you hold covers the chain so far.

The result names how far it verified, for example *Verified up to seq 47, covered by your receipt at seq 29, entries after seq 29 have no receipt*. If a link is broken, the card for that entry says so.

## The host key

Your browser pins the host's key when you join. If it later sees a different key, verification fails. A person who signed in with a pasted token skips the join, so the result says the key was not seen at join.

## Its limits

- It can only check what you may see. Other people's private entries reach you as hashes.
- Entries newer than your last receipt are linked, but no receipt covers them yet.
- It runs in code the host served you. For stronger assurance, build the web room yourself or read the log with your own tools.
