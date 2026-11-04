// SPDX-License-Identifier: Apache-2.0
// The mic and camera buttons. The camera is a plain file picker that asks for the back camera on a
// phone, so it works without HTTPS too; the photo is made smaller on the phone before it is sent.
import { type ChangeEvent, useId } from "react";
import { useRecorder } from "./useRecorder";
import { MAX_SECONDS } from "./wav";
import "./inputs.css";

export function MicIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" />
      <path
        d="M6 11a6 6 0 0 0 12 0M12 17v4M9 21h6"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CameraIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M4 8h3l2-3h6l2 3h3v11H4z"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="13" r="3.5" fill="currentColor" />
    </svg>
  );
}

export function MicButton({
  label,
  disabled,
  onClip,
  onProblem,
}: {
  label: string;
  disabled?: boolean;
  onClip: (wav: Blob) => void;
  onProblem: (text: string) => void;
}) {
  const rec = useRecorder(onClip, onProblem);
  const recording = rec.state === "recording";
  const busy = rec.state === "asking" || rec.state === "working";
  return (
    <button
      type="button"
      className="ck-in-btn"
      data-recording={recording}
      aria-pressed={recording}
      aria-label={recording ? `Stop recording (${rec.seconds} of ${MAX_SECONDS} s)` : label}
      title={recording ? "Stop" : label}
      disabled={disabled || busy}
      onClick={() => (recording ? rec.stop() : void rec.start())}
    >
      <MicIcon />
      {recording && <span className="ck-in-secs">{MAX_SECONDS - rec.seconds}s</span>}
    </button>
  );
}

const MAX_SIDE = 1280;

/** The photo as a JPEG at most 1280 px on its longest side; the original if that fails. */
export async function shrink(file: Blob): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const out = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, "image/jpeg", 0.85));
    return out ?? file;
  } catch {
    return file;
  }
}

export function CameraButton({
  label,
  disabled,
  onImage,
}: {
  label: string;
  disabled?: boolean;
  onImage: (image: Blob) => void;
}) {
  const id = useId();
  const picked = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) onImage(await shrink(file));
  };
  return (
    <label className="ck-in-btn" title={label} data-disabled={disabled === true} htmlFor={id}>
      <CameraIcon />
      <span className="tb-sr">{label}</span>
      <input
        id={id}
        type="file"
        accept="image/*"
        capture="environment"
        className="ck-in-file"
        disabled={disabled}
        onChange={picked}
      />
    </label>
  );
}
