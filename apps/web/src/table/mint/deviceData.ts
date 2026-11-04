// SPDX-License-Identifier: Apache-2.0
// `room.devices` from the viewer's state, read defensively, and the three device routes. Every call
// carries only the viewer token; the host decides who may mint, approve or send a frame.
import { assertAllowedBase, readConfig } from "../../feed/config";
import type { ViewerState } from "../../feed/delta";
import type { Call } from "../api";

export type DeviceStage = { name: string; state: string; took: number | null };
export type DeviceReadingRow = {
  field: string;
  value: number;
  unit: string;
  threshold: number;
  over: boolean;
};
export type Device = {
  id: string;
  label: string;
  template: string;
  state: "minting" | "approve" | "seated" | "failed";
  health: "live" | "offline";
  mine: boolean;
  canApprove: boolean;
  stages: DeviceStage[];
  error: string;
  tools: string[];
  needs: { id: string; title: string }[];
  attacks: { passed: number; total: number } | null;
  cost: number | null;
  elapsed: number | null;
  fields: { id: string; unit: string; threshold: number }[];
  reading: DeviceReadingRow[];
  readings: { field: string; value: number; t: number | null }[];
  hold: { need: string; start: string; end: string; state: string } | null;
};

type Raw = Record<string, unknown>;
const obj = (v: unknown): Raw =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Raw) : {};
const rows = (v: unknown): Raw[] => (Array.isArray(v) ? v.map(obj) : []);
const str = (v: unknown): string => (typeof v === "string" ? v : "");
const num = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const STATES = ["minting", "approve", "seated", "failed"] as const;

export function readDevices(state: ViewerState | null): Device[] {
  const room = obj(state?.room);
  return rows(room.devices)
    .filter((d) => str(d.id) !== "")
    .map((d) => {
      const attacks = obj(d.attacks);
      const hold = obj(d.hold);
      return {
        id: str(d.id),
        label: str(d.label) || str(d.id),
        template: str(d.template),
        state: STATES.find((s) => s === d.state) ?? "failed",
        health: d.health === "live" ? "live" : "offline",
        mine: d.mine === true,
        canApprove: d.can_approve === true,
        stages: rows(d.stages).map((s) => ({
          name: str(s.name),
          state: str(s.state),
          took: num(s.took),
        })),
        error: str(d.error),
        tools: (Array.isArray(d.tools) ? d.tools : []).map(str).filter(Boolean),
        needs: rows(d.needs).map((n) => ({ id: str(n.id), title: str(n.title) })),
        attacks:
          num(attacks.total) !== null
            ? { passed: num(attacks.passed) ?? 0, total: num(attacks.total) ?? 0 }
            : null,
        cost: num(d.cost_micro_usd),
        elapsed: num(d.elapsed),
        fields: rows(d.fields).map((f) => ({
          id: str(f.id),
          unit: str(f.unit),
          threshold: num(f.threshold) ?? 0,
        })),
        reading: rows(d.reading).map((r) => ({
          field: str(r.field),
          value: num(r.value) ?? 0,
          unit: str(r.unit),
          threshold: num(r.threshold) ?? 0,
          over: r.over === true,
        })),
        readings: rows(d.readings).map((r) => ({
          field: str(r.field),
          value: num(r.value) ?? 0,
          t: num(r.t),
        })),
        hold: str(hold.start)
          ? {
              need: str(hold.need),
              start: str(hold.start),
              end: str(hold.end),
              state: str(hold.state),
            }
          : null,
      };
    });
}

async function post<T>(path: string, body: FormData | object): Promise<Call<T>> {
  const config = readConfig();
  if (!config) return { ok: false, status: 401, error: "no_session", detail: "", auth: true };
  assertAllowedBase(config.baseUrl);
  const form = body instanceof FormData;
  const headers: Record<string, string> = { Authorization: `Bearer ${config.token}` };
  if (!form) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${config.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: form ? body : JSON.stringify(body),
    });
  } catch {
    return { ok: false, status: 0, error: "unreachable", detail: "", auth: false };
  }
  const json = obj(await res.json().catch(() => ({})));
  if (res.ok) return { ok: true, data: json as T };
  return {
    ok: false,
    status: res.status,
    error: str(json.error) || String(res.status),
    detail: str(json.detail),
    auth: res.status === 401,
  };
}

export const deviceIo = {
  mint: (form: FormData) => post<{ device: string }>("/v1/room/mint", form),
  approve: (device: string) => post<{ state: string }>("/v1/room/mint/approve", { device }),
  frame: (form: FormData) =>
    post<{ reading: DeviceReadingRow[]; rippled: string[] }>("/v1/room/mint/frame", form),
};
