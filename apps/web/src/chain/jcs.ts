// SPDX-License-Identifier: Apache-2.0
// RFC 8785 canonical JSON for values that came out of a JSON parser.

/** The largest integer a JSON number may carry on this wire: 2^53 - 1. */
export const MAX_SAFE = Number.MAX_SAFE_INTEGER;

export class CanonicalError extends Error {
  override name = "CanonicalError";
}

const encoder = new TextEncoder();

function hasLoneSurrogate(text: string): boolean {
  for (let i = 0; i < text.length; i++) {
    const unit = text.charCodeAt(i);
    if (unit >= 0xd800 && unit <= 0xdbff) {
      const next = text.charCodeAt(i + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return true;
      i++;
    } else if (unit >= 0xdc00 && unit <= 0xdfff) {
      return true;
    }
  }
  return false;
}

function quote(text: string): string {
  if (hasLoneSurrogate(text)) throw new CanonicalError("a string holds an unpaired surrogate");
  // The built-in escaper writes exactly the short escapes and lower-case \u00xx of RFC 8785.
  return JSON.stringify(text);
}

function number(value: number): string {
  if (!Number.isFinite(value)) throw new CanonicalError("a number is not finite");
  if (Object.is(value, -0)) return "0";
  // ECMAScript Number-to-string is the number form RFC 8785 prescribes.
  return String(value);
}

function write(value: unknown, out: string[]): void {
  if (value === null) {
    out.push("null");
  } else if (typeof value === "boolean") {
    out.push(value ? "true" : "false");
  } else if (typeof value === "number") {
    out.push(number(value));
  } else if (typeof value === "string") {
    out.push(quote(value));
  } else if (Array.isArray(value)) {
    out.push("[");
    value.forEach((item, index) => {
      if (index > 0) out.push(",");
      write(item, out);
    });
    out.push("]");
  } else if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    // Default string order compares UTF-16 code units, which is the order RFC 8785 asks for.
    const keys = Object.keys(record).sort();
    out.push("{");
    keys.forEach((key, index) => {
      if (index > 0) out.push(",");
      out.push(quote(key), ":");
      write(record[key], out);
    });
    out.push("}");
  } else {
    throw new CanonicalError(`a ${typeof value} is not JSON`);
  }
}

/** The canonical JSON text of a parsed value. */
export function canonicalize(value: unknown): string {
  const out: string[] = [];
  write(value, out);
  return out.join("");
}

/** The canonical bytes (UTF-8) of a parsed value. */
export function canonicalBytes(value: unknown): Uint8Array {
  return encoder.encode(canonicalize(value));
}

/**
 * Canonical text of raw JSON text. A parser cannot tell an integer from a float with a zero
 * fraction, so the wire text is scanned for integer literals beyond +-(2^53 - 1) and refuses them.
 */
export function canonicalizeText(json: string): string {
  assertSafeIntegers(json);
  return canonicalize(JSON.parse(json));
}

function assertSafeIntegers(json: string): void {
  let i = 0;
  while (i < json.length) {
    const ch = json.charAt(i);
    if (ch === '"') {
      i++;
      while (i < json.length && json.charAt(i) !== '"') i += json.charAt(i) === "\\" ? 2 : 1;
      i++;
    } else if (ch === "-" || (ch >= "0" && ch <= "9")) {
      let end = i + 1;
      while (end < json.length && /[0-9.eE+-]/.test(json.charAt(end))) end++;
      const token = json.slice(i, end);
      if (/^-?\d+$/.test(token) && BigInt(token) > BigInt(MAX_SAFE)) refuse(token);
      if (/^-\d+$/.test(token) && BigInt(token) < -BigInt(MAX_SAFE)) refuse(token);
      i = end;
    } else {
      i++;
    }
  }
}

function refuse(token: string): never {
  throw new CanonicalError(`integer ${token} is outside the safe range`);
}
