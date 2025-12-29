#!/bin/bash

# Couleurs pour le terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}   ALFAX OS - INSTALLATION AUTOMATIQUE      ${NC}"
echo -e "${BLUE}==============================================${NC}"

# 1. Mise à jour des dépôts
echo -e "${GREEN}[1/5] Mise à jour du système (apt update)...${NC}"
sudo apt update -y

# 2. Installation des dépendances système
echo -e "${GREEN}[2/5] Installation de Python et des libs SSH...${NC}"
# On installe python3-venv pour l'environnement isolé
# libffi-dev et libssl-dev sont obligatoires pour Paramiko (SSH)
sudo apt install -y python3 python3-pip python3-venv libffi-dev libssl-dev build-essential screen

# 3. Création de l'environnement virtuel (VENV)
echo -e "${GREEN}[3/5] Création de l'environnement virtuel Python...${NC}"
if [ -d "venv" ]; then
    echo "Le dossier venv existe déjà, passage à la suite."
else
    python3 -m venv venv
fi

# 4. Installation des dépendances Python
echo -e "${GREEN}[4/5] Installation de Flask, SocketIO et Paramiko...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install flask flask-socketio paramiko eventlet

# 5. Finalisation
echo -e "${GREEN}[5/5] Configuration des permissions...${NC}"
chmod +x start_serveur.sh 2>/dev/null || echo "Note: start_serveur.sh non trouvé, pense à le créer."

echo -e "${BLUE}==============================================${NC}"
echo -e "${GREEN}✅ INSTALLATION TERMINÉE AVEC SUCCÈS !${NC}"
echo -e "Tu peux maintenant lancer ton serveur avec :"
echo -e "${BLUE}./start_serveur.sh${NC}"
echo -e "${BLUE}==============================================${NC}"