// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { ConfirmRoute, confirmCode } from "./ConfirmRoute";
import { clearToken, readConfig, scrubAddress } from "./feed/config";
import { FeedProvider } from "./feed/useFeed";
import { Gallery } from "./gallery/Gallery";
import { Genesis } from "./genesis/Genesis";
import { Join } from "./genesis/Join";
import { LensView } from "./lens/LensView";
import { RoomView } from "./RoomView";
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
  useEffect(() => scrubAddress(), []);
  const enter = () => {
    setNotice(undefined);
    go("/");
    setPath("/");
    setConfig(readConfig());
  };
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
      ) : (
        <RoomView />
      )}
    </FeedProvider>
  );
}
