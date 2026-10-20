import { useState } from 'react';
import { NavLink, Route, Routes, Navigate } from 'react-router-dom';
import type { Campaign } from '../types';

const nav = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/campaigns', label: 'Campaigns', icon: '🎯' },
  { to: '/monitor', label: 'Run Monitor', icon: '📡' },
  { to: '/targets', label: 'Targets', icon: '🧩' },
  { to: '/findings', label: 'Findings', icon: '🔎' },
  { to: '/knowledge', label: 'Knowledge KB', icon: '📚' },
  { to: '/reports', label: 'Reports', icon: '📄' },
  { to: '/settings', label: 'Settings', icon: '⚙️' },
];

export function NavBar() {
  return (
    <header className="navbar">
      <div className="navbar__logo">
        <span className="navbar__logo-mark">⛨</span>
        <span className="navbar__logo-text">Vanguard-Breach</span>
      </div>
      <nav className="navbar__links">
        {nav.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className="navbar__link"
            end={to === '/'}
          >
            <span className="navbar__link-icon">{icon}</span>
            <span className="navbar__link-label">{label}</span>
          </NavLink>
        ))}
      </nav>
    </header>
  );
}

export function RouteOutlet() {
  return <Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/campaigns" element={<CampaignsPage />} />
    <Route path="/monitor" element={<RunMonitorPage />} />
    <Route path="/targets" element={<TargetsPage />} />
    <Route path="/findings" element={<FindingsPage />} />
    <Route path="/knowledge" element={<KnowledgePage />} />
    <Route path="/reports" element={<ReportsPage />} />
    <Route path="/settings" element={<SettingsPage />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}
