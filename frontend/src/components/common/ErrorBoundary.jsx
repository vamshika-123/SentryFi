import React from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service like Sentry
    console.error("ErrorBoundary caught an error", error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center animate-fade-in">
          <div className="glass-panel max-w-md p-8 border-danger/50 shadow-2xl shadow-danger/20">
            <AlertOctagon className="w-16 h-16 text-danger mx-auto mb-6" />
            <h1 className="text-2xl font-bold mb-3 text-slate-100">Application Error</h1>
            <p className="text-slate-400 mb-6 text-sm">
              The SentryFi interface encountered an unexpected error. Our threat engine remains secure, but the UI needs to be reloaded.
            </p>
            <div className="bg-slate-900/80 p-4 rounded-lg text-left overflow-hidden mb-6">
               <p className="text-danger-400 font-mono text-xs truncate">
                 {this.state.error && this.state.error.toString()}
               </p>
            </div>
            <button
              onClick={() => {
                this.setState({ hasError: false });
                window.location.reload();
              }}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children; 
  }
}

export default ErrorBoundary;
