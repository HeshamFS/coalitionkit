// SPDX-License-Identifier: Apache-2.0
// What the first screen shows, read from the host. The kit holds no rooms of its own.
export type Room = {
  id: string;
  goal: string;
  seats: number;
  filled: number;
  closes: string;
  lat: number;
  lon: number;
  status: "forming" | "acting";
  sample: boolean;
};

export type RoomList = { rooms: Room[]; examples: string[] };

export const NO_ROOMS: RoomList = { rooms: [], examples: [] };

export async function listRooms(
  signal?: AbortSignal,
  fetchFn: typeof fetch = (...a) => globalThis.fetch(...a),
): Promise<RoomList> {
  const res = await fetchFn("/v1/rooms", { method: "GET", signal });
  if (!res.ok) return NO_ROOMS;
  const body = (await res.json()) as Partial<RoomList>;
  return { rooms: body.rooms ?? [], examples: body.examples ?? [] };
}

/** A real room sends when it closes as a time; a sample's words are shown as they are. */
export function closesLabel(closes: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T/.test(closes)) return closes;
  const when = new Date(closes);
  if (Number.isNaN(when.getTime())) return "closes soon";
  return `closes ${when.toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit" })}`;
}

/** A point on the map, in percent of its width and height. */
export type Spot = { x: number; y: number };

/**
 * Fit the rooms into the map with room for their labels. The ground under them is drawn from a
 * pattern, so this keeps their relative places without claiming to be a street map.
 */
export function spots(rooms: Room[]): Spot[] {
  if (!rooms.length) return [];
  const lats = rooms.map((r) => r.lat);
  const lons = rooms.map((r) => r.lon);
  const [loLat, hiLat] = [Math.min(...lats), Math.max(...lats)];
  const [loLon, hiLon] = [Math.min(...lons), Math.max(...lons)];
  const share = (v: number, lo: number, hi: number) => (hi === lo ? 0.5 : (v - lo) / (hi - lo));
  const placed: Spot[] = [];
  for (const r of rooms) {
    const spot = {
      x: 14 + share(r.lon, loLon, hiLon) * 72,
      y: 16 + (1 - share(r.lat, loLat, hiLat)) * 68,
    };
    // Labels are wide. A room that would sit on another moves down a line, wrapping inside the map.
    for (let tries = 0; tries < 5 && placed.some((p) => crowded(p, spot)); tries++) {
      spot.y = spot.y + LINE > 84 ? 16 + ((spot.y + LINE) % 68) : spot.y + LINE;
    }
    placed.push(spot);
  }
  return placed;
}

const LINE = 17;

function crowded(a: Spot, b: Spot): boolean {
  return Math.abs(a.x - b.x) < 24 && Math.abs(a.y - b.y) < LINE;
}

const DOOR_CODE = /^[A-HJKMNP-Z2-9]{3}-[A-HJKMNP-Z2-9]{4}$/;

/** A room's short code, as a person might say or type it: any case, dash or not. */
export function doorCodeIn(text: string): string | null {
  const value = text.trim().toUpperCase().replace(/\s+/g, "");
  const dashed = /^[A-Z0-9]{7}$/.test(value) ? `${value.slice(0, 3)}-${value.slice(3)}` : value;
  return DOOR_CODE.test(dashed) ? dashed : null;
}

/** What a pasted link or typed code holds: an invitation's secret, or a room's short code. */
export function invitationIn(text: string): string | null {
  const value = text.trim();
  const secret = value.includes("#") ? value.slice(value.lastIndexOf("#") + 1) : value;
  return /^[A-Za-z0-9_-]{16,256}$/.test(secret) ? secret : doorCodeIn(secret);
}

export type Scanned = { secret: string } | { problem: "elsewhere" | "not-invitation" };

/** What a scanned QR holds. A link to another address is refused and never followed. */
export function scannedInvitation(text: string, origin: string): Scanned {
  const value = text.trim();
  if (/^[a-z][a-z0-9+.-]*:/i.test(value)) {
    try {
      if (new URL(value).origin !== origin) return { problem: "elsewhere" };
    } catch {
      return { problem: "not-invitation" };
    }
  }
  const secret = invitationIn(value);
  return secret ? { secret } : { problem: "not-invitation" };
}
