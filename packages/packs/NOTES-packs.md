# Notes for the lead: Discipline Pack format

Spec text proposed (the spec's pack section does not define these; nothing here is in a schema).

- Layout: every file key in `pack.yaml` is a path inside the pack folder. `vocabulary` is one
  YAML mapping from a core object (need, offer, task, resource, plan, commitment, tension,
  charter, decision) to a word, or to `{one, other}`. `views` is one YAML file with
  `components` (name to `{props, required, doors}`, the surfaces catalog shape) and `order`
  (role, then device `wide|compact|message|voice`, then a list of component names).
  `schemas` maps `need|offer|task|resource` to a JSON Schema file. `evals` lists one scenario
  file each, with optional `examples` (`{type, payload}`) run through the core payload schemas.
- `task_templates` (a brief item, absent from the spec table): a file `{templates: [{id,
  title, role?, requirements?, scope?}]}`. A template scope may be `host`, `self` or `roles`
  naming roles the pack declares; never `coalition` or named participants.
- Signature: `pack.sig` is JSON `{format: "coalitionkit-pack/v0", kid, public_key, sig}`.
  Signed bytes are the JCS form of `{format, files}`, `files` mapping every other file (POSIX
  path) to its SHA-256; `sig` is a detached compact JWS (EdDSA) as in contracts.
  `load_pack` needs `trusted_keys` and trusts only those; the embedded `public_key` proves
  integrity only (`verify_pack_embedded`).

Gaps and conflicts in the spec's pack section.

1. Policy actions: the spec says the loader accepts allow, redact, block or escalate; the
   steward's `PACK_ACTIONS` matches. The brief says a pack cannot add `block` or `quarantine`.
   The loader follows the brief (rejects block and quarantine). The spec needs one answer.
2. The `roles` value shape is not given; `{may: [...], label?}` is assumed. Role ids and the
   five abilities are checked, but the spec says nothing on how a pack role maps to charter
   roles or the authorization matrix.
3. `vocabulary`, `views`, `schemas`, `skills`, `mint`, `connectors`, `strategy` have no file
   format or semantics. "Extends the core payloads" for `schemas` is undefined: the loader only
   checks each is a valid 2020-12 schema that does not take a core `$id`. No extension point
   exists in the core payload schemas, and tasks and resources have no payload at all.
4. `mint`, `connectors`, `strategy`, `skills` are parsed and path-checked only; "each with its
   own tests" is not run. `fairness` values are assumed numeric.
5. "Vault access" is undefined. The loader refuses any `pack.yaml` key or connector name or
   command token containing "vault"; eval vault data is scenario data, not access.
6. The pack catalog extension: the spec does not say how a tree names the active packs, how
   renderers learn pack components (the closed catalog `coalitionkit/v0_9` is refused for any
   other ID) or whether pack components keep the catalog ID. `extend_catalog` keeps the core
   ID. The core catalog is not shipped as a file or constant, so callers pass a `Catalog`.
7. Scope: the spec has no pack scope rule. `check_not_wider` and `narrow` exist for the host;
   the loader cannot compare to a base scope, so it allows only host, self and declared roles.
8. `pack_violation` (check order step 12): nothing says how the host calls the pack policies
   (they run through the Steward engine as pack policies) or which pack policy wins on a tie.
9. The core range syntax (`>=0.1,<0.2`) is not specified beyond the example; comparators
   `>= <= == != > <` joined by commas are assumed, and pre-release tags are ignored.
10. Evals: no runner contract. `EvalScenario.check` compares an observed outcome to `expect`;
    how participants are scripted, how `canaries_leaked` is measured and what `decision` is
    compared by is not specified. The spec example's participant ids (`p1`) fit the id rule.
11. Unsigned packs: the spec does not say whether packs must be signed. The brief does; an
    unsigned pack validates (`inspect_pack`) but never loads (`load_pack`). Key distribution,
    revocation and pack versions pinned by a Coalition are open.
12. Pack words and the denylist: nothing in code reads pack words into
    `tools/discipline-denylist.txt` (tested). Fixtures are neutral.

Hooks wanted (surfaces and steward are unchanged): a `Catalog` constructor or a public
`ComponentSpec` export from `coalitionkit_surfaces` (the loader imports it from
`coalitionkit_surfaces.catalog`); a steward helper that loads a policy set from text so packs
need not read files themselves.
