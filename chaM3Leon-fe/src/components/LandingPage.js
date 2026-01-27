import React from 'react';

const LandingPage = () => {
  const services = [
    {
      name: 'Grafana',
      description: 'Monitoring e visualizzazione dati in tempo reale',
      icon: '📈',
      url: 'http://localhost:3001',
      color: '#FF6B35'
    },
    {
      name: 'Apache Spark',
      description: 'Elaborazione distribuita di big data',
      icon: '⚙️',
      url: 'http://localhost:8080',
      color: '#E25A3B'
    },
    {
      name: 'MLflow',
      description: 'Gestione del ciclo di vita ML',
      icon: '📋',
      url: 'http://localhost:5000',
      color: '#0194E2'
    },
    {
      name: 'Jupyter',
      description: 'Ambiente di sviluppo interattivo',
      icon: '💻',
      url: 'http://localhost:8888',
      color: '#F37626'
    },
    {
      name: 'Airflow',
      description: 'Orchestrazione di workflow automatizzati',
      icon: '🔄',
      url: 'http://localhost:8081',
      color: '#017CEE'
    },
    {
      name: 'MinIO',
      description: 'Storage distribuito per oggetti',
      icon: '💾',
      url: 'http://localhost:9001',
      color: '#C72E29'
    }
  ];

  const handleServiceClick = (url) => {
    window.open(url, '_blank');
  };

  return (
    <div className="container">
      <div className="card text-center">
        <div className="header-section">
          <h1>Chameleon Platform</h1>
          <p className="subtitle">
            Piattaforma integrata per Data Science e Machine Learning
          </p>
          <div className="divider"></div>
        </div>
        
        <div className="services-section">
          <h2>Servizi Disponibili</h2>
          <div className="grid">
            {services.map((service, index) => (
              <div 
                key={index} 
                className="service-card professional"
                onClick={() => handleServiceClick(service.url)}
              >
                <div className="service-header">
                  <span className="service-icon">{service.icon}</span>
                  <h3>{service.name}</h3>
                </div>
                <p className="service-description">{service.description}</p>
                <button 
                  className="btn btn-service"
                  style={{ borderColor: service.color, color: service.color }}
                >
                  Accedi a {service.name}
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="tools-section">
          <h2>Strumenti di Sviluppo</h2>
          <div className="tools-grid">
            <a href="/workflow-generator" className="tool-card">
              <div className="tool-icon">⚡</div>
              <h3>Workflow Generator</h3>
              <p>Crea e gestisci pipeline ML personalizzate</p>
            </a>
            <a href="/custom-page" className="tool-card">
              <div className="tool-icon">🛠️</div>
              <h3>Strumenti Personalizzati</h3>
              <p>Accedi a funzionalità avanzate e configurazioni</p>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;