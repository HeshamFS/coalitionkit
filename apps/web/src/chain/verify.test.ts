// @vitest-environment node
// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { canonicalize } from "./jcs";
import {
  type Envelope,
  entryHash,
  envelopeSignatureProblem,
  genesisHash,
  type LogEntry,
  sha256Hex,
  type VerifyInput,
  verifyLog,
} from "./verify";

// biome-ignore lint/suspicious/noExplicitAny: vectors are untyped JSON
const read = (name: string): any =>
  JSON.parse(
    readFileSync(
      fileURLToPath(new URL(`../../../../spec/vectors/${name}`, import.meta.url)),
      "utf8",
    ),
  );

const LOG = read("log.json");
const SIGNING = read("signing.json");
const b64 = (hexText: string) => Buffer.from(hexText, "hex").toString("base64url");
const clone = <T>(value: T): T => structuredClone(value);

const hostJwk = {
  kty: "OKP",
  crv: "Ed25519",
  kid: LOG.host_key.kid as string,
  x: b64(LOG.host_key.public_key_hex),
};
const hostPrivate = { ...hostJwk, d: b64(LOG.host_key.private_seed_hex) };
const ENTRIES: Envelope[] = LOG.entries;
const RECEIPTS: Envelope[] = LOG.receipts;
const G = LOG.genesis;
const payloadOf = (e: Envelope | undefined) => e?.payload as Record<string, unknown>;

const base = (over: Partial<VerifyInput> = {}): VerifyInput => ({
  coalitionId: G.coalition_id,
  hostCardUrl: G.host_card_url,
  createdAt: G.created_at,
  hostKey: hostJwk,
  entries: clone(ENTRIES),
  receipts: clone(RECEIPTS),
  ...over,
});

async function signAsHost(envelope: Envelope): Promise<Envelope> {
  const key = await crypto.subtle.importKey("jwk", hostPrivate, { name: "Ed25519" }, false, [
    "sign",
  ]);
  const body: Envelope = {};
  for (const [k, v] of Object.entries(envelope)) {
    if (!["sig", "seq", "ts", "prev_hash"].includes(k)) body[k] = v;
  }
  const header = Buffer.from(
    canonicalize({ alg: "EdDSA", typ: "JOSE", kid: hostJwk.kid }),
  ).toString("base64url");
  const payload = Buffer.from(canonicalize(body)).toString("base64url");
  const signature = await crypto.subtle.sign(
    { name: "Ed25519" },
    key,
    new TextEncoder().encode(`${header}.${payload}`),
  );
  return { ...envelope, sig: `${header}..${Buffer.from(signature).toString("base64url")}` };
}

async function projectionOf(entry: Envelope): Promise<Envelope> {
  return signAsHost({
    ext_version: "0.1",
    coalition_id: entry.coalition_id,
    event_id: `${entry.event_id}P`,
    type: "coalition.projection",
    sender: G.host_card_url,
    on_behalf_of: "host",
    scope: { audience: "participants", participants: ["p2"] },
    payload: {
      source: {
        event_id: entry.event_id,
        seq: entry.seq,
        type: entry.type,
        on_behalf_of: entry.on_behalf_of,
        prev_hash: entry.prev_hash,
        hash: await entryHash(entry),
      },
      payload: {},
    },
    seq: entry.seq,
    ts: entry.ts,
    prev_hash: entry.prev_hash,
  });
}

const toStub = async (e: Envelope) => ({
  seq: e.seq as number,
  prev_hash: e.prev_hash as string,
  hash: await entryHash(e),
});

const fails = (result: Awaited<ReturnType<typeof verifyLog>>) =>
  result.ok ? null : `${result.check}@${result.seq}`;

describe("log vectors", () => {
  it("genesis hash and head hashes match the vector", async () => {
    expect(await genesisHash(G.coalition_id, G.host_card_url, G.created_at)).toBe(G.hash);
    expect(await Promise.all(ENTRIES.map(entryHash))).toEqual(LOG.head_hashes);
  });

  it("the good log verifies end to end, covered by the last receipt", async () => {
    expect(await verifyLog(base())).toEqual({ ok: true, verifiedTo: 4, coveredByReceipt: 4 });
  });

  it("a log without receipts verifies and claims no coverage", async () => {
    expect(await verifyLog(base({ receipts: [] }))).toEqual({
      ok: true,
      verifiedTo: 4,
      coveredByReceipt: null,
    });
  });

  it("a wrong genesis input is a genesis failure at seq 1", async () => {
    expect(fails(await verifyLog(base({ createdAt: "2026-10-29T08:00:01Z" })))).toBe("genesis@1");
    expect(fails(await verifyLog(base({ hostCardUrl: `${G.host_card_url}x` })))).toBe("genesis@1");
  });

  it("a gap is found", async () => {
    const e = clone(ENTRIES);
    const entries = [e[0], e[2], e[3]] as LogEntry[];
    expect(fails(await verifyLog(base({ entries })))).toBe("gap@2");
  });

  it("an edit before the tail breaks the link after it", async () => {
    const e = clone(ENTRIES);
    payloadOf(e[1]).reason = "edited";
    expect(fails(await verifyLog(base({ entries: e })))).toBe("link@3");
  });

  it("an edited tail passes the chain but not the receipt", async () => {
    const e = clone(ENTRIES);
    payloadOf(e[3]).reason = "edited tail";
    expect(fails(await verifyLog(base({ entries: e })))).toBe("receipt@4");
    expect(await verifyLog(base({ entries: e, receipts: [] }))).toMatchObject({ ok: true });
  });

  it("an edit with a re-linked chain is caught by the receipt", async () => {
    const e = clone(ENTRIES);
    payloadOf(e[2]).reason = "edited";
    (e[3] as Envelope).prev_hash = await entryHash(e[2] as Envelope);
    expect(fails(await verifyLog(base({ entries: e })))).toBe("receipt@3");
  });

  for (const keep of [0, 1, 2, 3]) {
    it(`truncation to ${keep} entries is caught by the receipts`, async () => {
      const result = await verifyLog(base({ entries: clone(ENTRIES).slice(0, keep) }));
      expect(fails(result)).toBe(`receipt@${keep + 1}`);
      expect(result.ok ? "" : result.detail).toContain(`ends at seq ${keep}`);
    });
  }

  it("receipts cover only what they cover", async () => {
    const result = await verifyLog(
      base({ entries: clone(ENTRIES).slice(0, 2), receipts: clone(RECEIPTS).slice(0, 2) }),
    );
    expect(result).toEqual({ ok: true, verifiedTo: 2, coveredByReceipt: 2 });
  });

  it("stubs keep the chain and the receipts checkable", async () => {
    const mixed: LogEntry[] = [];
    for (const [i, e] of ENTRIES.entries()) mixed.push(i % 2 ? await toStub(clone(e)) : clone(e));
    expect(await verifyLog(base({ entries: mixed }))).toEqual({
      ok: true,
      verifiedTo: 4,
      coveredByReceipt: 4,
    });
    mixed[1] = { seq: 2, prev_hash: ENTRIES[1]?.prev_hash as string, hash: "f".repeat(64) };
    expect(fails(await verifyLog(base({ entries: mixed })))).toBe("link@3");
  });

  it("projections stand in through their stub once the host signature verifies", async () => {
    const mixed: LogEntry[] = [
      clone(ENTRIES[0] as Envelope),
      await projectionOf(ENTRIES[1] as Envelope),
      clone(ENTRIES[2] as Envelope),
      await projectionOf(ENTRIES[3] as Envelope),
    ];
    expect(await verifyLog(base({ entries: mixed }))).toEqual({
      ok: true,
      verifiedTo: 4,
      coveredByReceipt: 4,
    });
  });

  it("a forged projection is a signature failure, not a gap", async () => {
    const p = await projectionOf(ENTRIES[1] as Envelope);
    ((p.payload as Record<string, unknown>).source as Record<string, unknown>).hash = "0".repeat(
      64,
    );
    const mixed: LogEntry[] = [clone(ENTRIES[0] as Envelope), p, ...clone(ENTRIES).slice(2)];
    expect(fails(await verifyLog(base({ entries: mixed })))).toBe("signature@2");
  });

  it("a projection signed by another key is refused", async () => {
    const other = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    const jwk = (await crypto.subtle.exportKey("jwk", other.publicKey)) as JsonWebKey;
    const result = await verifyLog(
      base({
        hostKey: { ...jwk, kid: hostJwk.kid },
        entries: [await projectionOf(ENTRIES[0] as Envelope), ...clone(ENTRIES).slice(1)],
      }),
    );
    expect(fails(result)).toBe("signature@1");
  });

  it("a receipt with an edited head_hash or another Coalition fails", async () => {
    const forged = clone(RECEIPTS);
    payloadOf(forged[0]).head_hash = "0".repeat(64);
    expect(fails(await verifyLog(base({ receipts: forged })))).toBe("signature@1");
    const wrong = await signAsHost({
      ...clone(RECEIPTS[0] as Envelope),
      payload: { ...payloadOf(RECEIPTS[0]), coalition_id: "01M4XRC000000G40R40M30E20A" },
    });
    expect(fails(await verifyLog(base({ receipts: [wrong] })))).toBe("receipt@1");
  });

  it("a signed envelope that is not a receipt is refused", async () => {
    const other = await signAsHost({ ...clone(RECEIPTS[0] as Envelope), type: "coalition.leave" });
    expect(fails(await verifyLog(base({ receipts: [other] })))).toBe("receipt@1");
  });

  it("an unusable key is a signature failure when a signature must be checked", async () => {
    const result = await verifyLog(base({ hostKey: { kty: "OKP", crv: "Ed25519", x: "AA" } }));
    expect(fails(result)).toBe("signature@1");
  });
});

describe("signing vector", () => {
  const jwk = SIGNING.test_key.public_jwk;

  it("canonical payload, digest and the published JWS agree", async () => {
    const unsigned = Object.fromEntries(
      Object.entries(SIGNING.envelope_signed).filter(([k]) => k !== "sig"),
    );
    expect(canonicalize(unsigned)).toBe(SIGNING.signing_payload_utf8);
    const bytes = new TextEncoder().encode(SIGNING.signing_payload_utf8);
    expect(await sha256Hex(bytes)).toBe(SIGNING.signing_payload_sha256);
    expect(SIGNING.envelope_signed.sig).toBe(SIGNING.jws);
  });

  it("the signed envelope verifies, and still does once the host fields are added", async () => {
    expect(await envelopeSignatureProblem(SIGNING.envelope_signed, jwk)).toBeNull();
    expect(await envelopeSignatureProblem(SIGNING.envelope_accepted_by_host, jwk)).toBeNull();
    expect(SIGNING.accepted_still_verifies).toBe(true);
    expect(await entryHash(SIGNING.envelope_accepted_by_host)).toBe(SIGNING.prev_hash_of_accepted);
  });

  it("an edited envelope, a wrong key and a wrong kid do not verify", async () => {
    const edited = clone(SIGNING.envelope_signed);
    edited.payload.capacity = 3;
    expect(await envelopeSignatureProblem(edited, jwk)).not.toBeNull();
    expect(await envelopeSignatureProblem(SIGNING.envelope_signed, hostJwk)).not.toBeNull();
    const kid = await envelopeSignatureProblem(SIGNING.envelope_signed, { ...jwk, kid: "other" });
    expect(kid).toMatch(/kid/);
  });

  it("malformed signatures are refused", async () => {
    const env = SIGNING.envelope_signed;
    const bad = [undefined, "a.b.c", "x", `${SIGNING.protected_header_b64}.AA.AA`];
    for (const sig of bad) {
      expect(await envelopeSignatureProblem({ ...env, sig }, jwk)).not.toBeNull();
    }
  });
});
