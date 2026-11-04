// SPDX-License-Identifier: Apache-2.0
// A recording becomes a 16 kHz mono 16-bit PCM WAV before it leaves the phone: the host's
// transcriber takes WAV only, and browsers record webm/opus (Chrome) or mp4/aac (iOS Safari).
// Web Audio decodes whatever the browser recorded, and an offline context resamples and mixes down.

export const RATE = 16_000;
export const MAX_SECONDS = 20;

/** PCM samples in [-1, 1] as a WAV file: RIFF header, one channel, 16-bit little endian. */
export function encodeWav(samples: Float32Array, rate = RATE): ArrayBuffer {
  const bytes = samples.length * 2;
  const out = new DataView(new ArrayBuffer(44 + bytes));
  const text = (at: number, s: string) => {
    for (let i = 0; i < s.length; i++) out.setUint8(at + i, s.charCodeAt(i));
  };
  text(0, "RIFF");
  out.setUint32(4, 36 + bytes, true);
  text(8, "WAVE");
  text(12, "fmt ");
  out.setUint32(16, 16, true);
  out.setUint16(20, 1, true); // PCM
  out.setUint16(22, 1, true); // mono
  out.setUint32(24, rate, true);
  out.setUint32(28, rate * 2, true);
  out.setUint16(32, 2, true);
  out.setUint16(34, 16, true);
  text(36, "data");
  out.setUint32(40, bytes, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i] ?? 0));
    out.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return out.buffer;
}

type Ctx = typeof AudioContext;

/** Any recording the browser can decode, as at most 20 seconds of 16 kHz mono WAV. */
export async function toWav(recording: Blob): Promise<Blob> {
  const Live: Ctx | undefined =
    globalThis.AudioContext ??
    (globalThis as unknown as { webkitAudioContext?: Ctx }).webkitAudioContext;
  if (!Live || typeof OfflineAudioContext === "undefined") throw new Error("no Web Audio here");
  const live = new Live();
  let decoded: AudioBuffer;
  try {
    decoded = await live.decodeAudioData(await recording.arrayBuffer());
  } finally {
    void live.close();
  }
  const frames = Math.max(1, Math.min(Math.ceil(decoded.duration * RATE), MAX_SECONDS * RATE));
  const offline = new OfflineAudioContext(1, frames, RATE);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination); // a mono destination mixes every channel down
  source.start();
  const rendered = await offline.startRendering();
  return new Blob([encodeWav(rendered.getChannelData(0))], { type: "audio/wav" });
}
