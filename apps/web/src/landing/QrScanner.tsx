// SPDX-License-Identifier: Apache-2.0
// Reads a room's QR with the device camera and joins with the invitation inside it. The camera
// stops the moment this closes, and frames are only read here: nothing leaves the browser.
import { useEffect, useRef, useState } from "react";
import { scannedInvitation } from "./rooms";
import "./scanner.css";

const AIM = "Point your camera at the room's QR.";
const NO_CAMERA_HERE =
  "This address can't use the camera. Scan with your phone's camera app, or type the code.";
const CAMERA_OFF = "Camera access is off. Allow it in your browser, or type the code.";
const NO_CAMERA = "No camera found on this device. Type the code instead.";
const CAMERA_FAILED = "The camera didn't start. Type the code instead.";
const NOTES = {
  elsewhere: "That QR is for another address, so it wasn't opened.",
  "not-invitation": "That QR isn't a room invitation.",
} as const;

const READ_EVERY_MS = 200;
const LONGEST_SIDE = 720;

function cameraProblem(error: unknown): string {
  const name = error instanceof DOMException ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") return CAMERA_OFF;
  if (name === "NotFoundError" || name === "OverconstrainedError") return NO_CAMERA;
  return CAMERA_FAILED;
}

export function QrScanner({
  onJoin,
  onClose,
}: {
  onJoin: (secret: string) => void;
  onClose: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  const join = useRef(onJoin);
  join.current = onJoin;
  const [note, setNote] = useState(AIM);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    close.current?.focus();
    let stopped = false;
    let stream: MediaStream | undefined;
    let timer: ReturnType<typeof setInterval> | undefined;
    const stop = () => {
      stopped = true;
      clearInterval(timer);
      for (const track of stream?.getTracks() ?? []) track.stop();
    };
    const fail = (message: string) => {
      if (stopped) return;
      setFailed(true);
      setNote(message);
    };
    const start = async () => {
      if (!navigator.mediaDevices?.getUserMedia) return fail(NO_CAMERA_HERE);
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        });
      } catch (error) {
        return fail(cameraProblem(error));
      }
      if (stopped) return stop();
      const frame = document.createElement("canvas");
      try {
        const { default: readQr } = await import("jsqr");
        if (stopped) return;
        const el = video.current;
        if (!el) return;
        el.srcObject = stream;
        await el.play();
        if (stopped) return;
        timer = setInterval(() => {
          if (el.readyState < 2 || !el.videoWidth) return;
          const scale = Math.min(1, LONGEST_SIDE / Math.max(el.videoWidth, el.videoHeight));
          frame.width = Math.round(el.videoWidth * scale);
          frame.height = Math.round(el.videoHeight * scale);
          const paint = frame.getContext("2d", { willReadFrequently: true });
          if (!paint) return;
          paint.drawImage(el, 0, 0, frame.width, frame.height);
          const { data } = paint.getImageData(0, 0, frame.width, frame.height);
          const code = readQr(data, frame.width, frame.height);
          if (!code) return;
          const scanned = scannedInvitation(code.data, location.origin);
          if ("secret" in scanned) {
            stop();
            join.current(scanned.secret);
          } else setNote(NOTES[scanned.problem]);
        }, READ_EVERY_MS);
      } catch {
        fail(CAMERA_FAILED);
      }
    };
    void start();
    return stop;
  }, []);

  return (
    // The keys belong to the dialog as a whole: Escape closes, and Close is the only stop for Tab.
    <div
      className="ld-scanner"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ld-scanner-title"
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
        if (e.key === "Tab") e.preventDefault();
      }}
    >
      <div className="ld-scanner-card">
        <h2 id="ld-scanner-title">Scan a room's QR</h2>
        {!failed && (
          <div className="ld-scanner-view">
            <video ref={video} muted playsInline aria-label="Camera view" />
            <svg className="ld-scanner-aim" viewBox="0 0 100 100" aria-hidden="true">
              <path d="M2 20V8a6 6 0 0 1 6-6h12M80 2h12a6 6 0 0 1 6 6v12M98 80v12a6 6 0 0 1-6 6H80M20 98H8a6 6 0 0 1-6-6V80" />
            </svg>
          </div>
        )}
        <p role="status">{note}</p>
        <button ref={close} type="button" className="ld-scanner-close" onClick={onClose}>
          {failed ? "Back" : "Close"}
        </button>
      </div>
    </div>
  );
}
