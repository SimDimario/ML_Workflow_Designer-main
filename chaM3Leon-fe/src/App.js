import React from 'react';
import { BrowserRouter as Router, Routes, Route, Outlet } from 'react-router-dom';
import './App.css';

import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import LandingPage from './components/LandingPage';
import WorkflowGenerator from './components/WorkflowGenerator';
import CustomPage from './components/CustomPage';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import GoogleCallback from './components/RegisterGoogleCallbackPage';

// Layout per pagine che richiedono autenticazione
function MainLayout() {
  return (
    <>
      <Navbar />
      <div className="main-content">
        <Outlet />
      </div>
    </>
  );
}

// Layout per pagine di login/register (senza navbar)
function AuthLayout() {
  return (
    <div className="auth-content">
      <Outlet />
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        {/* Pagine di autenticazione */}
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/google-callback" element={<GoogleCallback />} />
        </Route>

        {/* Pagine protette */}
        <Route element={<MainLayout />}>
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <LandingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/workflow-generator"
            element={
              <ProtectedRoute>
                <WorkflowGenerator />
              </ProtectedRoute>
            }
          />
          <Route
            path="/custom-page"
            element={
              <ProtectedRoute>
                <CustomPage />
              </ProtectedRoute>
            }
          />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
