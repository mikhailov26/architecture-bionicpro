import { ReactKeycloakProvider } from "@react-keycloak/web";
import Keycloak, { KeycloakConfig } from "keycloak-js";
import React from "react";
import ReportPage from "./components/ReportPage";

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM || "",
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID || "",
};

const keycloak = new Keycloak(keycloakConfig);

const App: React.FC = () => {
  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={{
        flow: "standard",
        pkceMethod: "S256",
        onLoad: "login-required",
        checkLoginIframe: false,
      }}
      LoadingComponent={<div style={{ padding: 40 }}>Загрузка…</div>}
    >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

export default App;