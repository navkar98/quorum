import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import StudentApp from "./student/StudentApp";
import SecurityApp from "./security/SecurityApp";
import Landing from "./shared/Landing";
import "./shared/styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/student/*" element={<StudentApp />} />
        <Route path="/security/*" element={<SecurityApp />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
