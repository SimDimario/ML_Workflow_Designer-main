import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./LoginPage.css";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [googleLoaded, setGoogleLoaded] = useState(false);

  const navigate = useNavigate();

  /* =========================
     LOGIN CLASSICO
     ========================= */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Errore login");
      }

      const data = await res.json();
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      navigate("/");
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  /* =========================
     GOOGLE LOGIN (ID TOKEN → BACKEND)
     ========================= */
  useEffect(() => {
    // Funzione per inizializzare Google Sign-In
    const initializeGoogleSignIn = () => {
      if (window.google && window.google.accounts) {
        window.google.accounts.id.initialize({
          client_id: "51542307347-5bd6uee5uqtpggpskm30o3or8d4nqq0r.apps.googleusercontent.com",
          callback: handleGoogleResponse,
        });

        window.google.accounts.id.renderButton(
          document.getElementById("google-login-btn"),
          {
            theme: "outline",
            size: "large",
            width: "100%",
          }
        );
        
        setGoogleLoaded(true);
      }
    };

    // Controlla se lo script è già caricato
    if (window.google && window.google.accounts) {
      initializeGoogleSignIn();
    } else {
      // Carica lo script di Google se non presente
      const script = document.createElement("script");
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.onload = initializeGoogleSignIn;
      document.head.appendChild(script);

      // Cleanup: rimuovi lo script quando il componente viene smontato
      return () => {
        if (script.parentNode) {
          script.parentNode.removeChild(script);
        }
      };
    }
  }, []);

  const handleGoogleResponse = async (response) => {
    try {
      const res = await fetch("http://localhost:8000/auth/login/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: response.credential, // ID TOKEN GOOGLE
        }),
      });

      if (!res.ok) {
        throw new Error("Login con Google fallito");
      }

      const data = await res.json();

      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);

      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-title">Chameleon Platform</h1>
        <p className="login-subtitle">
          Accedi alla piattaforma di Data Science
        </p>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="login-error">{error}</div>}

          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button type="submit" disabled={loading}>
            {loading ? "Accesso in corso..." : "Accedi"}
          </button>
        </form>

        {/* GOOGLE LOGIN */}
        <div style={{ marginTop: "16px" }}>
          <div id="google-login-btn" />
          {!googleLoaded && (
            <div style={{
              width: "100%",
              height: "40px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "#f5f5f5",
              borderRadius: "4px",
              fontSize: "14px",
              color: "#666"
            }}>
              Caricamento Google Sign-In...
            </div>
          )}
        </div>

        <p style={{ marginTop: "20px" }}>
          Non hai un account? <Link to="/register">Registrati</Link>
        </p>
      </div>
    </div>
  );
}