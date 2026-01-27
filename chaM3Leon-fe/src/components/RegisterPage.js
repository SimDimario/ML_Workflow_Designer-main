import React, { useState, useEffect } from "react";
import { createUser } from "../services/auth";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import "./RegisterPage.css";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form, setForm] = useState({
    username: "",
    password: "",
    email: "",
    first_name: "",
    last_name: "",
  });
  const [error, setError] = useState(null);
  const [googleData, setGoogleData] = useState(null);
  const [isGoogleRegistration, setIsGoogleRegistration] = useState(false);

  // Controlla se arriva dalla registrazione Keycloak (non toccato)
  useEffect(() => {
    const email = searchParams.get("email");
    const firstName = searchParams.get("first_name");
    const lastName = searchParams.get("last_name");
    const fromGoogle = searchParams.get("from_google");

    if (fromGoogle && email) {
      setGoogleData({ email, firstName, lastName });
      setForm(prev => ({
        ...prev,
        email: email || "",
        first_name: firstName || "",
        last_name: lastName || "",
        username: email?.split("@")[0] || "",
      }));
    }
  }, [searchParams]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    
    try {
      if (isGoogleRegistration && googleData) {
        // DOPPIA REGISTRAZIONE: Google (Django) + Keycloak
        
        // 1️⃣ Registrazione su Django (Google OAuth)
        const googleResponse = await fetch("http://localhost:8000/auth/register/google", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: form.email,
            google_sub: googleData.google_sub,
            username: form.username,
            first_name: form.first_name,
            last_name: form.last_name,
          }),
        });

        if (!googleResponse.ok) {
          const errorData = await googleResponse.json();
          throw new Error(errorData.error || "Errore durante la registrazione con Google");
        }

        const googleData_response = await googleResponse.json();
        
        // 2️⃣ Registrazione parallela su Keycloak (con password)
        // Genera una password casuale per Keycloak (l'utente non la userà mai)
        const keycloakPassword = form.password || `Google_${Math.random().toString(36).slice(-12)}`;
        
        try {
          await createUser({
            username: form.username,
            password: keycloakPassword,
            email: form.email,
            first_name: form.first_name,
            last_name: form.last_name,
          });
        } catch (keycloakError) {
          console.warn("Registrazione Keycloak fallita, ma Django OK:", keycloakError);
          // Non blocchiamo il flusso se Keycloak fallisce
        }
        
        // Salva i token JWT di Django
        localStorage.setItem("access_token", googleData_response.access);
        localStorage.setItem("refresh_token", googleData_response.refresh);
        
        // Reindirizza alla home o dashboard
        navigate("/");
      } else {
        // Registrazione normale solo Keycloak (non toccato)
        await createUser(form);
        navigate("/login");
      }
    } catch (err) {
      setError(err.message || "Errore durante la registrazione");
    }
  };

  // Registrazione con Google OAuth (popup)
  const registerWithGoogle = () => {
    const GOOGLE_CLIENT_ID = "51542307347-5bd6uee5uqtpggpskm30o3or8d4nqq0r.apps.googleusercontent.com"; // ⚠️ Inserisci il tuo Client ID Google
    
    // ⚠️ IMPORTANTE: Questo URL DEVE essere identico a quello in Google Cloud Console
    const REDIRECT_URI = "http://localhost:3000/google-callback";
    
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=token id_token&scope=openid email profile&nonce=${Date.now()}&prompt=select_account`;
    
    // Apri popup per login Google
    const width = 500;
    const height = 600;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    
    const popup = window.open(
      authUrl,
      "Google Login",
      `width=${width},height=${height},left=${left},top=${top}`
    );

    // Ascolta il messaggio dal popup
    const handleMessage = async (event) => {
      if (event.origin !== window.location.origin) return;
      
      if (event.data.type === "GOOGLE_AUTH_SUCCESS") {
        const idToken = event.data.idToken;
        
        try {
          // Chiama l'endpoint di prefill
          const response = await fetch("http://localhost:8000/auth/google/prefill", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ token: idToken }),
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || "Errore durante il recupero dei dati Google");
          }

          const data = await response.json();
          
          // Compila il form con i dati di Google
          setGoogleData({
            email: data.email,
            firstName: data.first_name,
            lastName: data.last_name,
            avatar: data.avatar,
            google_sub: data.google_sub,
          });
          
          setForm(prev => ({
            ...prev,
            email: data.email,
            first_name: data.first_name,
            last_name: data.last_name,
            username: data.email.split("@")[0], // Pre-compila username
          }));
          
          setIsGoogleRegistration(true);
          
        } catch (err) {
          setError(err.message || "Errore durante il recupero dei dati Google");
        }
        
        popup?.close();
        window.removeEventListener("message", handleMessage);
      }
    };

    window.addEventListener("message", handleMessage);
  };

  return (
    <div className="auth-container">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h2>Registrazione</h2>
        <p className="auth-subtitle">
          Crea un account per accedere a Chameleon
        </p>

        {error && <div className="auth-error">{error}</div>}

         {googleData && isGoogleRegistration && (
          <div style={{
            backgroundColor: "#e6f7ff",
            border: "1px solid #91d5ff",
            padding: "12px",
            borderRadius: "8px",
            marginBottom: "15px",
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: "10px"
          }}>
            <div style={{
              width: "40px",
              height: "40px",
              borderRadius: "50%",
              backgroundColor: "white",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
            }}>
              <svg width="24" height="24" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
            </div>
            <div>
              <strong>✅ Dati ricevuti da Google</strong>
              <br />
              <small>Completa la registrazione</small>
            </div>
          </div>
        )}

        <div className="auth-grid">
          <input
            name="username"
            placeholder="Username"
            value={form.username}
            onChange={handleChange}
            required
          />

          <input
            name="email"
            placeholder="Email"
            value={form.email}
            onChange={handleChange}
            disabled={isGoogleRegistration || !!googleData}
            required
          />

          <input
            name="first_name"
            placeholder="Nome"
            value={form.first_name}
            onChange={handleChange}
          />

          <input
            name="last_name"
            placeholder="Cognome"
            value={form.last_name}
            onChange={handleChange}
          />

          <input
            type="password"
            name="password"
            placeholder={isGoogleRegistration ? "Password" : "Password"}
            onChange={handleChange}
            required={!isGoogleRegistration}
          />
          
          
        </div>

        <button type="submit" className="auth-button">
          Registrati
        </button>

        {!isGoogleRegistration && (
          <>
            <div style={{ margin: "15px 0", color: "#999", fontSize: "14px" }}>
              oppure
            </div>

            <button
              type="button"
              className="google-btn"
              onClick={registerWithGoogle}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "10px",
                width: "100%",
                padding: "12px",
                backgroundColor: "#fff",
                border: "1px solid #ddd",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "16px",
                fontWeight: "500",
                transition: "all 0.3s"
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Registrati con Google
            </button>
          </>
        )}

        <p className="auth-footer">
          Hai già un account? <Link to="/login">Login</Link>
        </p>
      </form>
    </div>
  );
}