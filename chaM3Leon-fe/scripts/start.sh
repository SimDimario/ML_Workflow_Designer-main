#!/bin/bash

echo "Avvio Chameleon Frontend..."

# Installa le dipendenze se non esistono
if [ ! -d "node_modules" ]; then
    echo "Installazione dipendenze..."
    npm install
fi

# Avvia l'applicazione
echo "Avvio dell'applicazione..."
npm start