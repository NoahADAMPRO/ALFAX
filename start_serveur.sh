#!/bin/bash

# --- CONFIGURATION ---
SESSION_NAME="alfax_server"
PORT=5001

# Couleurs pour le terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}--- ALFAX OS : Gestionnaire de serveur ---${NC}"

# 1. Vérification de l'environnement virtuel
if [ ! -d "venv" ]; then
    echo -e "${RED}Erreur : Le dossier 'venv' est introuvable.${NC}"
    echo "Lance d'abord ./install.sh pour configurer le serveur."
    exit 1
fi

# 2. Nettoyage : On ferme l'ancienne session si elle tourne déjà
if screen -list | grep -q "\.${SESSION_NAME}"; then
    echo -e "${BLUE}Une instance tourne déjà. Redémarrage...${NC}"
    screen -S $SESSION_NAME -X quit > /dev/null 2>&1
    sleep 1
fi

# 3. Lancement du serveur dans Screen
echo -e "${GREEN}Lancement du serveur sur le port $PORT...${NC}"
# -d -m lance la session en arrière-plan (detached)
screen -dmS $SESSION_NAME bash -c "source venv/bin/activate && python3 app.py"

# 4. Affichage du statut
sleep 2
if screen -list | grep -q "\.${SESSION_NAME}"; then
    echo -e "${GREEN}✅ Serveur opérationnel !${NC}"
    echo "-------------------------------------------------------"
    echo -e "Accès Web : ${BLUE}http://$(hostname -I | awk '{print $1}'):$PORT${NC}"
    echo "-------------------------------------------------------"
    echo -e "COMMANDES UTILES :"
    echo -e "- Voir la console : ${GREEN}screen -r $SESSION_NAME${NC}"
    echo -e "- Sortir de la console (sans couper) : ${BLUE}CTRL+A puis D${NC}"
    echo -e "- Arrêter le serveur : ${RED}screen -S $SESSION_NAME -X quit${NC}"
    echo "-------------------------------------------------------"
else
    echo -e "${RED}❌ Le serveur n'a pas pu démarrer. Vérifie tes fichiers.${NC}"
fi