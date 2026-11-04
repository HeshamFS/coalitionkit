// SPDX-License-Identifier: Apache-2.0
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import type { TableCtx } from "../context";
import { TableContext } from "../context";
import { type Call, mockIo } from "../fixtureIo";
import { act, BRIEF, base } from "../fixtures";
import { readRoom } from "../room";
import { BriefInputs } from "./BriefInputs";
import type { InputsIo, Reading } from "./io";
import { inputsIo } from "./io";
import { SayInputs } from "./SayInputs";
import { voiceMarks } from "./VoiceMarks";
import { encodeWav } from "./wav";

const ascii = (view: DataView, at: number, n: number) =>
  String.fromCharCode(...Array.from({ length: n }, (_, i) => view.getUint8(at + i)));

const read = (over: Partial<Reading>): Reading => ({
  text: "",
  ms: 900,
  answer: null,
  words: "",
  description: "",
  ...over,
});

function fakeInputs(reply: Reading, log: unknown[][]): InputsIo {
  return {
    voice: async (wav, q) => {
      log.push(["voice", wav.type, q]);
      return { ok: true, data: reply };
    },
    photo: async (image, q) => {
      log.push(["photo", image.type, q]);
      return { ok: true, data: reply };
    },
    say: async (text, via) => {
      log.push(["say", text, via]);
      return { ok: true, data: { route: "room", reply: "" } };
    },
  };
}

function withTable(node: ReactNode, calls: Call[], said: unknown[] = []) {
  const ctx = {
    room: base({ phase: "brief" }),
    io: mockIo(calls),
    setSaid: (s: unknown) => said.push(s),
  } as unknown as TableCtx;
  return render(<TableContext.Provider value={ctx}>{node}</TableContext.Provider>);
}

describe("phone inputs", () => {
  it("writes a 16 kHz mono 16-bit PCM WAV", () => {
    const view = new DataView(encodeWav(new Float32Array([0, 1, -1, 0.5])));
    expect(ascii(view, 0, 4)).toBe("RIFF");
    expect(ascii(view, 8, 4)).toBe("WAVE");
    expect(view.getUint16(20, true)).toBe(1);
    expect(view.getUint16(22, true)).toBe(1);
    expect(view.getUint32(24, true)).toBe(16_000);
    expect(view.getUint16(34, true)).toBe(16);
    expect(view.getUint32(40, true)).toBe(8);
    expect(view.getInt16(46, true)).toBe(0x7fff);
    expect(view.getInt16(48, true)).toBe(-0x8000);
  });

  it("sends the clip as the raw body with the viewer token and reads the reply", async () => {
    const seen: { url: string; init?: RequestInit }[] = [];
    const io = inputsIo(
      async (url, init) => {
        seen.push({ url: String(url), init });
        return new Response(
          JSON.stringify({ text: "about four hours", ms: 1200, answer: 4, words: "4 hours" }),
          { status: 200 },
        );
      },
      () => ({ baseUrl: "", token: "tok" }),
    );
    const wav = new Blob([new Uint8Array(8)], { type: "audio/wav" });
    const r = await io.voice(wav, "q2");
    expect(r).toMatchObject({ ok: true, data: { text: "about four hours", answer: 4 } });
    expect(seen[0]?.url).toBe("/v1/room/voice?question_id=q2");
    const headers = seen[0]?.init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok");
    expect(headers["Content-Type"]).toBe("audio/wav");
    expect(seen[0]?.init?.body).toBe(wav);
    await io.photo(new Blob(["x"], { type: "image/jpeg" }));
    expect(seen[1]?.url).toBe("/v1/room/photo?purpose=say");
    await io.say("hello", "voice");
    expect(JSON.parse(String(seen[2]?.init?.body))).toEqual({ text: "hello", via: "voice" });
  });

  it("reads the mark and the viewer's own inputs from the feed", () => {
    const room = readRoom({
      room: {
        ...base({}),
        activity: [
          { ...act({ id: "a1", verb: "saying", label: "Said", seat: "p1" }), source: "voice" },
          { ...act({ id: "a2", verb: "saying", label: "Said", seat: "p2" }), source: "host" },
        ],
        mine: { ...base({}).mine, inputs: [{ kind: "photo", text: "Three boxes", ms: 900 }] },
      },
    });
    expect(room).not.toBeNull();
    if (!room) return;
    expect(voiceMarks(room)).toEqual([{ seat: "p1", id: "a1", source: "voice" }]);
    expect(room.activity[0]?.source).toBe("host");
    expect(room.mine.inputs).toEqual([{ kind: "photo", text: "Three boxes", ms: 900 }]);
  });

  it("answers a question from a photo only when the person says to use it", async () => {
    const calls: Call[] = [];
    const log: unknown[][] = [];
    const reply = read({ answer: "o2", words: "Sat 10:00", description: "A calendar page." });
    const item = BRIEF[0];
    if (!item) throw new Error("no question");
    withTable(<BriefInputs item={item} io={fakeInputs(reply, log)} />, calls);
    const photo = new File(["img"], "shelf.jpg", { type: "image/jpeg" });
    await userEvent.upload(screen.getByLabelText("Answer with a photo"), photo);
    expect(await screen.findByText("A calendar page.")).toBeInTheDocument();
    expect(screen.getByText("Sat 10:00")).toBeInTheDocument();
    expect(log[0]).toEqual(["photo", "image/jpeg", "q1"]);
    expect(calls).toEqual([]);
    await userEvent.click(screen.getByRole("button", { name: "Use this answer" }));
    await waitFor(() => expect(calls).toEqual([{ name: "brief", args: ["q1", { value: "o2" }] }]));
  });

  it("says nothing it could not read, and lets the person fix the words before they go", async () => {
    const calls: Call[] = [];
    const said: unknown[] = [];
    const log: unknown[][] = [];
    const reply = read({ text: "We have two chairs.", words: "We have two chairs." });
    withTable(<SayInputs locked={false} io={fakeInputs(reply, log)} />, calls, said);
    const photo = new File(["img"], "chairs.jpg", { type: "image/jpeg" });
    await userEvent.upload(screen.getByLabelText("Show it with a photo"), photo);
    const box = await screen.findByLabelText("The words to send");
    await userEvent.clear(box);
    await userEvent.type(box, "everyone: we have two chairs");
    await userEvent.click(screen.getByRole("button", { name: "Say it" }));
    await waitFor(() => expect(said).toHaveLength(1));
    expect(log.at(-1)).toEqual(["say", "everyone: we have two chairs", "photo"]);
    expect(screen.queryByLabelText("The words to send")).toBeNull();
  });

  it("keeps the buttons shut while the say box is shut", () => {
    withTable(<SayInputs locked io={fakeInputs(read({}), [])} />, []);
    expect(screen.getByRole("button", { name: "Say it by voice" })).toBeDisabled();
    expect(screen.getByLabelText("Show it with a photo")).toBeDisabled();
  });
});
