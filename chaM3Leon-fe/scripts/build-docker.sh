#!/bin/bash

echo "Build dell'immagine Docker..."

# Build dell'immagine
docker build -t chameleon-fe .

echo "✅ Build completato!"
echo "Per avviare: docker-compose up -d"