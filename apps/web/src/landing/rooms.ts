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
  return rooms.map((r) => ({
    x: 14 + share(r.lon, loLon, hiLon) * 72,
    y: 16 + (1 - share(r.lat, loLat, hiLat)) * 68,
  }));
}

/** The secret in a pasted invitation: a whole `/join#…` link, or the secret alone. */
export function invitationIn(text: string): string | null {
  const value = text.trim();
  const secret = value.includes("#") ? value.slice(value.lastIndexOf("#") + 1) : value;
  return /^[A-Za-z0-9_-]{16,256}$/.test(secret) ? secret : null;
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
