// SPDX-License-Identifier: Apache-2.0
// A picture the host keeps for a room (`/v1/room/media/<sha-256>`) needs the viewer's bearer
// token, which an <img> cannot send. This fetches it with the token, only from an allowed base,
// and hands the image a local object URL. Any other source is passed through untouched.
import { useEffect, useState } from "react";
import { assertAllowedBase, readConfig } from "../../feed/config";

export const HOST_MEDIA = /^\/v1\/room\/media\/[0-9a-f]{64}$/;

/** The bytes of a room picture, fetched with the viewer token from an allowed base only. */
export async function fetchHostMedia(src: string): Promise<Blob> {
  if (!HOST_MEDIA.test(src)) throw new Error("not a room picture");
  const config = readConfig();
  if (!config) throw new Error("not signed in");
  assertAllowedBase(config.baseUrl);
  const r = await fetch(`${config.baseUrl}${src}`, {
    headers: { Authorization: `Bearer ${config.token}` },
  });
  if (!r.ok) throw new Error(String(r.status));
  return r.blob();
}

export function useHostSrc(src: string): { src: string; failed: boolean } {
  const hosted = HOST_MEDIA.test(src);
  const [local, setLocal] = useState("");
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!hosted) return;
    let url = "";
    let live = true;
    setLocal("");
    setFailed(false);
    fetchHostMedia(src)
      .then((blob) => {
        url = URL.createObjectURL(blob);
        if (live) setLocal(url);
        else URL.revokeObjectURL(url);
      })
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [hosted, src]);
  return hosted ? { src: local, failed } : { src, failed: false };
}
