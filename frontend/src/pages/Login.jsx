import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, signUp } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e, isSignup = false) => {
    e.preventDefault();
    try {
      setError('');
      setLoading(true);
      if (isSignup) {
        await signUp(email, password);
      } else {
        await login(email, password);
      }
      navigate('/dashboard');
    } catch (err) {
      setError('Failed to log in. Please check credentials or create an account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
         <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-[100px]"></div>
         <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-[100px]"></div>
      </div>

      <div className="glass-panel w-full max-w-md p-8 relative z-10">
        <div className="flex flex-col items-center mb-8">
          <Shield className="w-16 h-16 text-primary mb-4 drop-shadow-[0_0_15px_rgba(59,130,246,0.5)]" />
          <h1 className="text-3xl font-bold text-center mb-2">SentryFi</h1>
          <p className="text-slate-400 text-center">Threat Intelligence Engine</p>
        </div>

        {error && (
          <div className="bg-danger/20 border border-danger/50 text-danger-400 p-3 rounded-lg mb-6 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={(e) => handleSubmit(e, false)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Email</label>
            <input
              type="email"
              required
              className="input-field w-full"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
            <input
              type="password"
              required
              className="input-field w-full"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="btn-primary w-full shadow-[0_0_15px_rgba(59,130,246,0.3)] hover:shadow-[0_0_25px_rgba(59,130,246,0.5)]"
          >
            {loading ? 'Authenticating...' : 'Secure Login'}
          </button>
          
          <button
            type="button"
            onClick={(e) => handleSubmit(e, true)}
            disabled={loading}
            className="w-full text-sm text-slate-400 hover:text-primary transition-colors mt-4"
          >
            Don't have an account? Sign up
          </button>
        </form>
      </div>
    </div>
  );
}
