import React from 'react';
import { Link,useNavigate } from 'react-router-dom';
import './Navbar.css';
import '../services/auth'; // Assicurati che il servizio auth sia importato
import { logout } from '../services/auth';

const Navbar = () => {
 const navigate = useNavigate();

   console.log('🔴 NAVBAR STA VENENDO RENDERIZZATA!');

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      navigate("/login");
    }
  };

  return (
    <nav className="navbar">
      <div className="nav-container">
        <div className="nav-logo">
          <Link to="/">Chameleon</Link>
        </div>
        <ul className="nav-menu">
          <li className="nav-item">
            <Link to="/" className="nav-link">Home</Link>
          </li>
          <li className="nav-item">
            <Link to="/workflow-generator" className="nav-link">
                 Workflow Generator
            </Link>
          </li>
          <li className="nav-item">
            <Link to="/custom-page" className="nav-link">Strumenti</Link>
          </li>
          <li className="nav-item">
            <Link
              to="/login"
              className="nav-link logout-link"
              onClick={handleLogout}
            >
              Logout
            </Link>
          </li>
        
          
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;