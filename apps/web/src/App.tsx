// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { ConfirmRoute, confirmCode } from "./ConfirmRoute";
import { clearToken, readConfig, scrubAddress } from "./feed/config";
import { FeedProvider } from "./feed/useFeed";
import { Gallery } from "./gallery/Gallery";
import { LensView } from "./lens/LensView";
import { RoomView } from "./RoomView";
import { SignIn } from "./SignIn";

export const EXPIRED_NOTICE = "Your session ended. Sign in again.";

export function App() {
  const [config, setConfig] = useState(() => readConfig());
  const [notice, setNotice] = useState<string | undefined>();
  const [code] = useState(() => confirmCode(location.pathname));
  useEffect(() => scrubAddress(), []);
  if (location.pathname.startsWith("/gallery")) return <Gallery />;
  if (!config) {
    return (
      <SignIn
        notice={notice}
        onDone={() => {
          setNotice(undefined);
          setConfig(readConfig());
        }}
      />
    );
  }
  return (
    <FeedProvider
      config={config}
      onSignedOut={(reason) => {
        clearToken();
        setNotice(reason === "expired" ? EXPIRED_NOTICE : undefined);
        setConfig(null);
      }}
    >
      {code ? (
        <ConfirmRoute code={code} config={config} />
      ) : location.pathname.startsWith("/lens") ? (
        <LensView />
      ) : (
        <RoomView />
      )}
    </FeedProvider>
  );
}
