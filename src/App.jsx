import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import ProtectedRoute from './context/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import PhishingScanner from './pages/Scanners/PhishingScanner';
import InvoiceScanner from './pages/Scanners/InvoiceScanner';
import ComplianceScanner from './pages/Scanners/ComplianceScanner';
import History from './pages/History';
import ErrorBoundary from './components/common/ErrorBoundary';
function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="scanners/phishing" element={<PhishingScanner />} />
          <Route path="scanners/invoice" element={<InvoiceScanner />} />
          <Route path="scanners/compliance" element={<ComplianceScanner />} />
          <Route path="history" element={<History />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}

export default App;
