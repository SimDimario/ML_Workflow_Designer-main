import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import keycloak from './keycloak';


/*
try {
    const authenticate= keycloak.init({
        onLoad: 'login-required',
        
        });
    if (authenticate) {
    */
      const root = ReactDOM.createRoot(document.getElementById('root'));
      root.render(
      
        <App />
  
      
    );
    /*
        console.log('User is authenticated');
    } else {
        console.log('User is not authenticated');
    }
} catch (error) {
    console.error('Failed to initialize adapter:', error);
}*/