#!/bin/bash
# Snoozolène — Installation sur Linux (Debian/Ubuntu)
set -e

echo "=== Snoozolène — Installation ==="

# Docker
if ! command -v docker &> /dev/null; then
    echo "Installation de Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "Docker installé. Reconnectez-vous puis relancez ce script."
    exit 0
fi

# Lancement
echo "Démarrage des services..."
docker compose up -d --build

echo ""
echo "✓ Snoozolène est lancé !"
echo ""
echo "  Écran patient  : http://localhost:3000/display"
echo "  Interface aidant : http://localhost:3000/admin"
echo "  API            : http://localhost:8000"
echo ""
echo "Pour le mode kiosk (écran TV plein écran) :"
echo "  chromium --kiosk --noerrdialogs --disable-infobars http://localhost:3000/display"
