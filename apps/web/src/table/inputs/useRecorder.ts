// SPDX-License-Identifier: Apache-2.0
// Press to record, press again to stop; it stops by itself at 20 seconds. The microphone is
// released as soon as the clip ends, and the clip lives only in memory until it is sent.
import { useEffect, useRef, useState } from "react";
import { MAX_SECONDS, toWav } from "./wav";

export type RecorderState = "idle" | "asking" | "recording" | "working";

export function micAvailable(): boolean {
  return (
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined"
  );
}

export function useRecorder(onClip: (wav: Blob) => void, onProblem: (text: string) => void) {
  const [state, setState] = useState<RecorderState>("idle");
  const [seconds, setSeconds] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const timers = useRef<ReturnType<typeof setInterval>[]>([]);
  const clear = () => {
    for (const t of timers.current) clearInterval(t);
    timers.current.length = 0;
  };
  useEffect(() => {
    const live = timers.current;
    return () => {
      for (const t of live) clearInterval(t);
      const r = recorder.current;
      if (r && r.state !== "inactive") r.stop();
    };
  }, []);

  async function start() {
    if (!micAvailable()) {
      onProblem("This browser cannot record here. The microphone needs HTTPS or localhost.");
      return;
    }
    setState("asking");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setState("idle");
      onProblem("The microphone was not allowed. Type it instead.");
      return;
    }
    const parts: Blob[] = [];
    const r = new MediaRecorder(stream);
    recorder.current = r;
    r.ondataavailable = (e) => {
      if (e.data.size > 0) parts.push(e.data);
    };
    r.onstop = async () => {
      clear();
      for (const track of stream.getTracks()) track.stop();
      setState("working");
      try {
        onClip(await toWav(new Blob(parts, { type: r.mimeType })));
      } catch {
        onProblem("That recording could not be read. Try again, or type it.");
      }
      setState("idle");
    };
    const began = Date.now();
    setSeconds(0);
    timers.current.push(
      setInterval(() => {
        const s = Math.floor((Date.now() - began) / 1000);
        setSeconds(s);
        if (s >= MAX_SECONDS && r.state === "recording") r.stop();
      }, 250),
    );
    r.start();
    setState("recording");
  }

  function stop() {
    const r = recorder.current;
    if (r && r.state === "recording") r.stop();
  }

  return { state, seconds, start, stop };
}
