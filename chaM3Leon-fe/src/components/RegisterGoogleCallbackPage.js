import React, { useEffect } from "react";

export default function GoogleCallback() {
  useEffect(() => {
    // Estrai l'id_token dall'hash dell'URL
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    const idToken = params.get("id_token");

    if (idToken && window.opener) {
      // Invia il token alla finestra principale
      window.opener.postMessage(
        {
          type: "GOOGLE_AUTH_SUCCESS",
          idToken: idToken,
        },
        window.location.origin
      );
      
      // Chiudi automaticamente il popup dopo l'invio
      setTimeout(() => window.close(), 500);
    } else {
      console.error("Token non trovato o finestra principale non disponibile");
      // Opzionale: mostra un messaggio di errore
    }
  }, []);

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      height: "100vh",
      fontFamily: "Arial, sans-serif"
    }}>
      <div style={{ textAlign: "center" }}>
        <div style={{
          width: "50px",
          height: "50px",
          border: "4px solid #f3f3f3",
          borderTop: "4px solid #3498db",
          borderRadius: "50%",
          animation: "spin 1s linear infinite",
          margin: "0 auto 20px"
        }}></div>
        <p>Autenticazione in corso...</p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
}