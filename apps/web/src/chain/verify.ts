// SPDX-License-Identifier: Apache-2.0
// The reader checks of "The authenticated log boundary", run in the browser with WebCrypto only.
import { canonicalBytes } from "./jcs";

export type Envelope = Record<string, unknown>;
/** A replay entry outside the reader's scope: its place in the chain and nothing else. */
export type Stub = { seq: number; prev_hash: string; hash: string };
export type LogEntry = Envelope | Stub;

export type VerifyInput = {
  coalitionId: string;
  hostCardUrl: string;
  createdAt: string;
  /** The host public key pinned at join, as an Ed25519 JWK. */
  hostKey: JsonWebKey & { kid?: string };
  /** Originals, host-signed `coalition.projection` envelopes and stubs, in seq order. */
  entries: LogEntry[];
  /** Host-signed `coalition.receipt` envelopes the viewer kept. */
  receipts: Envelope[];
};

export type CheckName = "signature" | "gap" | "genesis" | "link" | "receipt";

export type Failure = { ok: false; seq: number; check: CheckName; detail: string };
export type VerifyResult =
  | { ok: true; verifiedTo: number; coveredByReceipt: number | null }
  | Failure;

type Bytes = Uint8Array<ArrayBuffer>;
type KeyGetter = () => Promise<CryptoKey>;
type Link = { seq: number; prev: unknown; hash: string };

const UNSIGNED = new Set(["sig", "seq", "ts", "prev_hash"]);

function fail(seq: number, check: CheckName, detail: string): Failure {
  return { ok: false, seq, check, detail };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** True for `{seq, prev_hash, hash}`: an entry that carries no envelope. */
export function isStub(entry: LogEntry): entry is Stub {
  return typeof (entry as Envelope).type !== "string" && typeof entry.hash === "string";
}

function toHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer), (b) => b.toString(16).padStart(2, "0")).join("");
}

export async function sha256Hex(bytes: Bytes): Promise<string> {
  return toHex(await crypto.subtle.digest("SHA-256", bytes));
}

function fromBase64Url(text: string): Bytes | null {
  if (!/^[A-Za-z0-9_-]*$/.test(text) || text.length % 4 === 1) return null;
  const padded =
    text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4);
  const raw = atob(padded);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

function toBase64Url(bytes: Uint8Array): string {
  let raw = "";
  for (const b of bytes) raw += String.fromCharCode(b);
  return btoa(raw).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** The sha256 hex of the genesis inputs: the `prev_hash` of seq 1. */
export function genesisHash(coalitionId: string, hostCardUrl: string, createdAt: string) {
  const inputs = { coalition_id: coalitionId, host_card_url: hostCardUrl, created_at: createdAt };
  return sha256Hex(canonicalBytes(inputs) as Bytes);
}

/** The hash the next entry must carry as `prev_hash`: sha256 of the JCS form, `sig` included. */
export function entryHash(entry: Envelope): Promise<string> {
  return sha256Hex(canonicalBytes(entry) as Bytes);
}

function importHostKey(jwk: VerifyInput["hostKey"]): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "jwk",
    { kty: jwk.kty, crv: jwk.crv, x: jwk.x },
    { name: "Ed25519" },
    false,
    ["verify"],
  );
}

type Header = { part: string; kid: string; signature: Bytes };

function parseSig(sig: unknown): Header | string {
  if (typeof sig !== "string") return "the envelope has no sig";
  const parts = sig.split(".");
  if (parts.length !== 3 || parts[1] !== "")
    return "sig is not a compact JWS with a detached payload";
  const [part = "", , signaturePart = ""] = parts;
  const headerBytes = fromBase64Url(part);
  const signature = fromBase64Url(signaturePart);
  if (!headerBytes || !signature) return "sig is not base64url";
  let header: unknown;
  try {
    header = JSON.parse(new TextDecoder().decode(headerBytes));
  } catch {
    return "the protected header is not JSON";
  }
  if (!isRecord(header)) return "the protected header is not an object";
  if (Object.keys(header).sort().join(",") !== "alg,kid,typ") {
    return "the protected header must hold exactly alg, typ and kid";
  }
  if (header.alg !== "EdDSA" || header.typ !== "JOSE" || typeof header.kid !== "string") {
    return "unsupported protected header";
  }
  return { part, kid: header.kid, signature };
}

/** Verify `envelope.sig` (compact JWS, detached payload) against the key. Null means it verifies. */
async function signatureProblem(
  envelope: Envelope,
  key: KeyGetter,
  expectedKid: string | undefined,
): Promise<string | null> {
  const header = parseSig(envelope.sig);
  if (typeof header === "string") return header;
  if (expectedKid !== undefined && header.kid !== expectedKid) return "kid is not the pinned key";
  const body: Envelope = {};
  for (const [name, value] of Object.entries(envelope)) if (!UNSIGNED.has(name)) body[name] = value;
  try {
    const signed = new TextEncoder().encode(`${header.part}.${toBase64Url(canonicalBytes(body))}`);
    const good = await crypto.subtle.verify(
      { name: "Ed25519" },
      await key(),
      header.signature,
      signed as Bytes,
    );
    return good ? null : "the signature does not verify";
  } catch (error) {
    return error instanceof Error ? error.message : "the signature cannot be checked";
  }
}

/** Check one envelope's `sig` against a pinned Ed25519 JWK. Null means it verifies. */
export async function envelopeSignatureProblem(
  envelope: Envelope,
  jwk: VerifyInput["hostKey"],
): Promise<string | null> {
  return signatureProblem(envelope, () => importHostKey(jwk), jwk.kid);
}

function pinnedKid(input: VerifyInput): string | undefined {
  return typeof input.hostKey.kid === "string" ? input.hostKey.kid : undefined;
}

async function projectionLink(
  entry: Envelope,
  where: number,
  input: VerifyInput,
  key: KeyGetter,
): Promise<Link | Failure> {
  const problem = await signatureProblem(entry, key, pinnedKid(input));
  if (problem) return fail(where, "signature", `projection: ${problem}`);
  const source = isRecord(entry.payload) ? entry.payload.source : undefined;
  if (
    !isRecord(source) ||
    typeof source.seq !== "number" ||
    typeof source.hash !== "string" ||
    typeof source.prev_hash !== "string"
  ) {
    return fail(where, "signature", "projection: no usable source stub");
  }
  return { seq: source.seq, prev: source.prev_hash, hash: source.hash };
}

/** Turn entries into chain links; a projection is verified first and stands in as its stub. */
async function toLinks(input: VerifyInput, key: KeyGetter): Promise<Link[] | Failure> {
  const links: Link[] = [];
  for (const [index, entry] of input.entries.entries()) {
    if (isStub(entry)) {
      links.push({ seq: entry.seq, prev: entry.prev_hash, hash: entry.hash });
    } else if (entry.type === "coalition.projection") {
      const where = typeof entry.seq === "number" ? entry.seq : index + 1;
      const link = await projectionLink(entry, where, input, key);
      if ("ok" in link) return link;
      links.push(link);
    } else if (typeof entry.seq !== "number") {
      return fail(index + 1, "gap", "an entry has no seq");
    } else {
      try {
        links.push({ seq: entry.seq, prev: entry.prev_hash, hash: await entryHash(entry) });
      } catch (error) {
        return fail(entry.seq, "link", error instanceof Error ? error.message : "cannot hash");
      }
    }
  }
  return links;
}

function chainProblem(links: Link[], genesis: string): Failure | null {
  let expectedPrev = genesis;
  let expectedSeq = 1;
  for (const link of links) {
    if (link.seq !== expectedSeq) {
      return fail(expectedSeq, "gap", `expected seq ${expectedSeq}, found ${link.seq}`);
    }
    if (link.prev !== expectedPrev) {
      if (expectedSeq === 1)
        return fail(1, "genesis", "prev_hash of seq 1 is not the genesis hash");
      return fail(expectedSeq, "link", `prev_hash at seq ${expectedSeq} does not link`);
    }
    expectedPrev = link.hash;
    expectedSeq++;
  }
  return null;
}

type Kept = { seq: number; head: string };

async function keptReceipts(input: VerifyInput, key: KeyGetter): Promise<Kept[] | Failure> {
  const kept: Kept[] = [];
  for (const receipt of input.receipts) {
    const body = isRecord(receipt.payload) ? receipt.payload : {};
    const seq = typeof body.seq === "number" ? body.seq : 0;
    const problem = await signatureProblem(receipt, key, pinnedKid(input));
    if (problem) return fail(seq, "signature", `receipt: ${problem}`);
    if (
      receipt.type !== "coalition.receipt" ||
      typeof body.head_hash !== "string" ||
      !Number.isInteger(body.seq) ||
      body.coalition_id !== input.coalitionId ||
      receipt.coalition_id !== input.coalitionId
    ) {
      return fail(seq, "receipt", "not a receipt for this Coalition");
    }
    kept.push({ seq, head: body.head_hash });
  }
  return kept.sort((a, b) => a.seq - b.seq);
}

function receiptProblem(kept: Kept[], links: Link[]): Failure | null {
  for (const item of kept) {
    if (item.seq > links.length)
      return fail(item.seq, "receipt", `the log ends at seq ${links.length}`);
    if (links[item.seq - 1]?.hash !== item.head) {
      return fail(item.seq, "receipt", `the entry at seq ${item.seq} was changed`);
    }
  }
  return null;
}

/**
 * Run the reader checks, first failure wins: host signatures of projections and receipts, then
 * gap-free seq from 1, the genesis link and each `prev_hash`, then every kept receipt.
 */
export async function verifyLog(input: VerifyInput): Promise<VerifyResult> {
  let cached: Promise<CryptoKey> | undefined;
  const key: KeyGetter = () => {
    cached ??= importHostKey(input.hostKey);
    return cached;
  };
  const links = await toLinks(input, key);
  if ("ok" in links) return links;
  const genesis = await genesisHash(input.coalitionId, input.hostCardUrl, input.createdAt);
  const broken = chainProblem(links, genesis);
  if (broken) return broken;
  const kept = await keptReceipts(input, key);
  if ("ok" in kept) return kept;
  const uncovered = receiptProblem(kept, links);
  if (uncovered) return uncovered;
  const last = kept[kept.length - 1];
  return { ok: true, verifiedTo: links.length, coveredByReceipt: last ? last.seq : null };
}
