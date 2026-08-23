import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { 
  LayoutDashboard, 
  ShieldAlert, 
  FileSearch, 
  FileText, 
  History, 
  LogOut
} from 'lucide-react';
import clsx from 'clsx';

export default function Layout() {
  const { logout, currentUser } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error("Logout failed", error);
    }
  };

  const navItems = [
    { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/scanners/phishing", icon: ShieldAlert, label: "Phishing Scanner" },
    { to: "/scanners/invoice", icon: FileSearch, label: "Invoice Scanner" },
    { to: "/scanners/compliance", icon: FileText, label: "Compliance Scanner" },
    { to: "/history", icon: History, label: "Scan History" },
  ];

  return (
    <div className="flex h-screen bg-background text-text-primary">
      {/* Sidebar */}
      <aside className="w-64 bg-surface border-r border-border flex flex-col hidden md:flex">
        {/* Wordmark — no icon, no gradient */}
        <div className="p-6 flex items-center border-b border-border">
          <h1 className="text-xl font-bold text-primary tracking-tight">
            SentryFi
          </h1>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-150 text-sm font-medium",
                  isActive
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : "text-text-secondary hover:bg-surface-alt hover:text-text-primary"
                )
              }
            >
              <item.icon className="w-4 h-4 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User footer */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3 px-3 py-2 mb-1 rounded-lg bg-surface-alt">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
              {currentUser?.displayName?.charAt(0) || currentUser?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                {currentUser?.displayName || currentUser?.email}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2 w-full text-left text-text-secondary text-sm hover:text-danger hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden bg-surface border-b border-border p-4 flex items-center justify-between">
          <h1 className="text-lg font-bold text-primary tracking-tight">SentryFi</h1>
          <button onClick={handleLogout} className="text-text-secondary hover:text-danger transition-colors">
            <LogOut className="w-5 h-5" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
