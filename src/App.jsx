// src/App.jsx
import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import NavBar from "./components/NavBar";

// Placeholder page components
import Dashboard from "./pages/Dashboard";
import CityMap from "./pages/CityMap";
import Infrastructure from "./pages/Infrastructure";
import Recovery from "./pages/Recovery";
import Simulation from "./pages/Simulation";
import Analytics from "./pages/Analytics";
import Alerts from "./pages/Alerts";
import Reports from "./pages/Reports";
import AdminPanel from "./pages/AdminPanel";

const App = () => {
  return (
    <Router>
      <div className="flex flex-col min-h-screen">
        <NavBar />
        <main className="flex-1 container mx-auto p-4">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/map" element={<CityMap />} />
            <Route path="/infrastructure/*" element={<Infrastructure />} />
            <Route path="/recovery/*" element={<Recovery />} />
            <Route path="/simulation/*" element={<Simulation />} />
            <Route path="/analytics/*" element={<Analytics />} />
            <Route path="/alerts/*" element={<Alerts />} />
            <Route path="/reports/*" element={<Reports />} />
            <Route path="/admin/*" element={<AdminPanel />} />
            {/* Add more routes as needed */}
          </Routes>
        </main>
        {/* Footer could be added here */}
      </div>
    </Router>
  );
};

export default App;
