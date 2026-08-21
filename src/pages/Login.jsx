import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Shield, 
  Lock, 
  Mail, 
  Eye, 
  EyeOff, 
  Sparkles, 
  ArrowRight, 
  AlertCircle, 
  CheckCircle2,
  Cpu,
  UserCheck
} from 'lucide-react';

export default function Login() {
  const [isSignUp, setIsSignUp] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { login, signUp, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please fill in all fields.');
      return;
    }
    
    try {
      setError('');
      setLoading(true);
      if (isSignUp) {
        await signUp(email, password);
      } else {
        await login(email, password);
      }
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    try {
      setError('');
      setLoading(true);
      await loginWithGoogle();
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Google sign in was cancelled or failed.');
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 md:p-8 relative overflow-hidden">
      {/* Dynamic Background Glowing Orbs */}
      <div className="absolute top-1/4 left-1/4 w-[450px] h-[450px] bg-primary/15 rounded-full blur-[120px] pointer-events-none animate-pulse"></div>
      <div className="absolute bottom-1/4 right-1/4 w-[450px] h-[450px] bg-emerald-500/10 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="w-full max-w-lg relative z-10">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="relative mb-3">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-blue-600 to-emerald-400 p-[1px] shadow-[0_0_30px_rgba(59,130,246,0.4)]">
              <div className="w-full h-full bg-surface rounded-2xl flex items-center justify-center">
                <Shield className="w-8 h-8 text-primary" />
              </div>
            </div>
            <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-background animate-ping"></div>
            <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-background"></div>
          </div>
          
          <h1 className="text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-200 to-emerald-400">
            SentryFi
          </h1>
          <p className="text-slate-400 text-sm mt-1 max-w-xs">
            Intelligent Financial Threat & Regulatory Compliance Engine
          </p>
        </div>

        {/* Main Card */}
        <div className="glass-panel p-8 backdrop-blur-xl border border-slate-700/60 shadow-2xl shadow-black/60 rounded-2xl">
          {/* Mode Switch Tabs */}
          <div className="grid grid-cols-2 p-1 bg-slate-900/80 rounded-xl mb-6 border border-slate-800">
            <button
              type="button"
              onClick={() => { setIsSignUp(false); setError(''); }}
              className={`py-2.5 text-sm font-semibold rounded-lg transition-all ${
                !isSignUp 
                  ? 'bg-primary text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]' 
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setIsSignUp(true); setError(''); }}
              className={`py-2.5 text-sm font-semibold rounded-lg transition-all ${
                isSignUp 
                  ? 'bg-primary text-white shadow-[0_0_15px_rgba(59,130,246,0.3)]' 
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-danger/10 border border-danger/30 text-danger text-sm flex items-start gap-3 animate-fade-in">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="flex-1 text-xs leading-relaxed">{error}</div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Work Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  placeholder="analyst@enterprise.com"
                  className="input-field w-full pl-10 pr-4 py-2.5 text-sm bg-slate-900/70 border-slate-700/80 focus:border-primary"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  placeholder="••••••••••••"
                  className="input-field w-full pl-10 pr-10 py-2.5 text-sm bg-slate-900/70 border-slate-700/80 focus:border-primary"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-3 mt-2 flex items-center justify-center gap-2 text-sm font-semibold tracking-wide shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:shadow-[0_0_25px_rgba(59,130,246,0.5)]"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>{isSignUp ? 'Register Account' : 'Authenticate & Enter'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Social Divider */}
          <div className="relative my-6 text-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800"></div>
            </div>
            <span className="relative px-3 bg-surface text-xs text-slate-500 uppercase tracking-widest font-mono">
              Or Connect With
            </span>
          </div>

          {/* Google Button */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl border border-slate-700/80 bg-slate-900/50 hover:bg-slate-800 text-slate-200 text-sm font-medium flex items-center justify-center gap-3 transition-colors"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
              />
              <path
                fill="#34A853"
                d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.35 24 12 24z"
              />
              <path
                fill="#FBBC05"
                d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 10.03 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
              />
              <path
                fill="#EA4335"
                d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.35 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
              />
            </svg>
            <span>Continue with Google</span>
          </button>

        </div>

        {/* Security badge footer */}
        <div className="flex items-center justify-center gap-2 mt-6 text-xs text-slate-500">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span>Protected with AES-256 Cloud Firestore & ML inference isolation</span>
        </div>
      </div>
    </div>
  );
}
