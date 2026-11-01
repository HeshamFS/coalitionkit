// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { ConfirmRoute, confirmCode } from "./ConfirmRoute";
import { clearToken, readConfig, scrubAddress } from "./feed/config";
import { FeedProvider } from "./feed/useFeed";
import { Gallery } from "./gallery/Gallery";
import { Genesis } from "./genesis/Genesis";
import { Join } from "./genesis/Join";
import { clearOwner } from "./genesis/owner";
import { LensView } from "./lens/LensView";
import type { DissolveEvent } from "./moments/Dissolve";
import { RoomView } from "./RoomView";
import { EndedView } from "./room/endCoalition";
import { beginEnd, clearEnded, readEnded, useEndRun } from "./room/ended";
import { GlassesRoute } from "./room/glasses";
import { SignIn } from "./SignIn";

export const EXPIRED_NOTICE = "Your session ended. Sign in again.";

function go(path: string) {
  globalThis.history.replaceState(null, "", path);
}

export function App() {
  const [config, setConfig] = useState(() => readConfig());
  const [notice, setNotice] = useState<string | undefined>();
  const [code] = useState(() => confirmCode(location.pathname));
  const [path, setPath] = useState(() => location.pathname);
  const [ended, setEnded] = useState<DissolveEvent | null>(null);
  const run = useEndRun();
  useEffect(() => scrubAddress(), []);
  const enter = () => {
    setNotice(undefined);
    go("/");
    setPath("/");
    setConfig(readConfig());
  };
  const leave = () => {
    beginEnd(null);
    setEnded(null);
    setConfig(null);
    enter();
  };
  if (run) return <EndedView run={run} onLeave={leave} />;
  if (ended) return <EndedView event={ended} onLeave={leave} />;
  if (path.startsWith("/gallery")) return <Gallery />;
  if (path.startsWith("/join")) return <Join onJoined={enter} />;
  if (!config) {
    if (code || path.startsWith("/signin") || notice)
      return <SignIn notice={notice} onDone={() => (code ? setConfig(readConfig()) : enter())} />;
    return <Genesis onEnter={enter} />;
  }
  return (
    <FeedProvider
      config={config}
      onSignedOut={(reason) => {
        clearToken();
        clearOwner();
        if (reason === "expired" && readEnded()) {
          setEnded(readEnded());
          setConfig(null);
          return;
        }
        clearEnded();
        if (!code) {
          go("/signin");
          setPath("/signin");
        }
        setNotice(reason === "expired" ? EXPIRED_NOTICE : undefined);
        setConfig(null);
      }}
    >
      {code ? (
        <ConfirmRoute code={code} config={config} />
      ) : path.startsWith("/lens") ? (
        <LensView />
      ) : path.startsWith("/glasses") ? (
        <GlassesRoute />
      ) : (
        <RoomView />
      )}
    </FeedProvider>
  );
}
