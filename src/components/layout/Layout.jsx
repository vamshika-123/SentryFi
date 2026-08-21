import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { 
  LayoutDashboard, 
  ShieldAlert, 
  FileSearch, 
  FileText, 
  History, 
  LogOut,
  Shield
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
    <div className="flex h-screen bg-background text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 glass-panel border-l-0 border-t-0 border-b-0 rounded-none flex flex-col hidden md:flex">
        <div className="p-6 flex items-center gap-3 border-b border-slate-700/50">
          <Shield className="w-8 h-8 text-primary" />
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
            SentryFi
          </h1>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200",
                  isActive 
                    ? "bg-primary/20 text-primary border border-primary/30 shadow-[0_0_15px_rgba(59,130,246,0.15)]" 
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                )
              }
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>
        
        <div className="p-4 border-t border-slate-700/50">
          <div className="flex items-center gap-3 px-3 py-2 mb-2 rounded-lg bg-slate-800/40 border border-slate-700/40">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-emerald-400 flex items-center justify-center text-sm font-bold text-white shadow-sm">
              {currentUser?.displayName?.charAt(0) || currentUser?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-slate-200 truncate">
                {currentUser?.displayName || currentUser?.email}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span className="text-[10px] text-slate-400 font-mono">
                  Verified Auth
                </span>
              </div>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-2 w-full text-left text-slate-400 hover:text-danger hover:bg-danger/10 rounded-lg transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden glass-panel rounded-none border-t-0 border-x-0 p-4 flex items-center justify-between">
           <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-primary" />
            <h1 className="text-lg font-bold">SentryFi</h1>
          </div>
          <button onClick={handleLogout} className="text-slate-400">
            <LogOut className="w-5 h-5" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-4 md:p-8 relative">
          {/* Subtle background glow effect */}
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-[100px] -z-10 pointer-events-none"></div>
          
          <Outlet />
        </div>
      </main>
    </div>
  );
}
