#!/bin/bash

# Script d'installation - Suivi Candidatures (Linux)

echo ""
echo "===================================="
echo " Installation - Suivi Candidatures"
echo "===================================="
echo ""

# Vérifier et installer Node.js
echo "Vérification de Node.js..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js n'est pas installé"
    echo ""
    echo "Installation de Node.js..."
    
    # Détecter la distribution Linux
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        
        case "$ID" in
            ubuntu|debian)
                sudo apt-get update
                sudo apt-get install -y nodejs npm
                ;;
            fedora)
                sudo dnf install -y nodejs npm
                ;;
            arch)
                sudo pacman -S nodejs npm
                ;;
            *)
                echo "Distribution non reconnue. Installez Node.js manuellement depuis:"
                echo "https://nodejs.org/"
                exit 1
                ;;
        esac
    else
        echo "Impossible de détecter votre distribution Linux"
        echo "Installez Node.js manuellement depuis: https://nodejs.org/"
        exit 1
    fi
fi

NODE_VERSION=$(node --version)
echo "✓ Node.js $NODE_VERSION détecté"

echo "Vérification de npm..."
NPM_VERSION=$(npm --version)
echo "✓ npm $NPM_VERSION détecté"

# Installation des dépendances
echo ""
echo "Installation des dépendances..."
npm install
if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de l'installation des dépendances"
    exit 1
fi
echo "✓ Dépendances installées"

# Créer le fichier .env
echo ""
echo "Configuration du fichier .env..."
if [ -f .env ]; then
    echo "Le fichier .env existe déjà. Passage..."
else
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ Fichier .env créé à partir de .env.example"
    else
        echo "❌ Le fichier .env.example est manquant"
        exit 1
    fi
fi

# Générer un secret NextAuth
echo ""
echo "Génération du secret NextAuth..."
if command -v openssl &> /dev/null; then
    NEXTAUTH_SECRET=$(openssl rand -base64 32)
else
    # Fallback si openssl n'est pas disponible
    NEXTAUTH_SECRET=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
fi

# Mettre à jour le fichier .env
sed -i "s|your-secret-here-replace-me|${NEXTAUTH_SECRET}|g" .env
sed -i 's|^DATABASE_URL=.*|DATABASE_URL="file:./prisma/dev.db"|g' .env

echo "✓ Fichier .env configuré"

# Configuration de la base de données
echo ""
echo "Configuration de la base de données..."
npx prisma migrate dev --name init
if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de la migration"
    exit 1
fi
echo "✓ Base de données configurée"

# Instructions finales
echo ""
echo "===================================="
echo " Installation terminée! ✓"
echo "===================================="
echo ""
echo "Pour démarrer l'application:"
echo "  npm run dev"
echo ""
echo "L'application sera disponible à:"
echo "  http://localhost:3000"
echo ""
echo "Credentials par défaut:"
echo "  Utilisateur: admin"
echo "  Mot de passe: admin123"
echo ""
