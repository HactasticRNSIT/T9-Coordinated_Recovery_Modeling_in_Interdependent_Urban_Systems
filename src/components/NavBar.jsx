// src/components/NavBar.jsx
import React from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { name: "Dashboard", path: "/dashboard" },
  { name: "City Map", path: "/map" },
  { name: "Infrastructure", path: "/infrastructure" },
  { name: "Recovery", path: "/recovery" },
  { name: "Simulation", path: "/simulation" },
  { name: "Analytics", path: "/analytics" },
  { name: "Alerts", path: "/alerts" },
  { name: "Reports", path: "/reports" },
  { name: "Admin", path: "/admin" },
];

const NavBar = () => {
  return (
    <nav className="bg-primary text-white shadow-md">
      <div className="container mx-auto px-4 py-2 flex items-center justify-between">
        <div className="text-xl font-semibold">UrbanSync</div>
        <ul className="flex space-x-4">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  isActive
                    ? "bg-secondary rounded px-3 py-1"
                    : "hover:bg-secondary/70 rounded px-3 py-1"
                }
              >
                {item.name}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
};

export default NavBar;
