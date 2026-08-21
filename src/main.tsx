import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import AdminSecurityPanel from "./AdminSecurityPanel";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
    <AdminSecurityPanel />
  </React.StrictMode>,
);
