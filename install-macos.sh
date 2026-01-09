#!/bin/bash

# Script d'installation - Suivi Candidatures (macOS)

echo ""
echo "===================================="
echo " Installation - Suivi Candidatures"
echo "===================================="
echo ""

# Vérifier si Homebrew est installé
echo "Vérification de Homebrew..."
if ! command -v brew &> /dev/null; then
    echo "Homebrew n'est pas installé"
    echo "Installation de Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    if [ $? -ne 0 ]; then
        echo "❌ Erreur lors de l'installation de Homebrew"
        exit 1
    fi
fi
echo "✓ Homebrew détecté"

# Vérifier et installer Node.js
echo "Vérification de Node.js..."
if ! command -v node &> /dev/null; then
    echo "Installation de Node.js via Homebrew..."
    brew install node
    
    if [ $? -ne 0 ]; then
        echo "❌ Erreur lors de l'installation de Node.js"
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
NEXTAUTH_SECRET=$(openssl rand -base64 32)

# Mettre à jour le fichier .env (macOS utilise sed -i avec un suffixe)
sed -i '' "s|your-secret-here-replace-me|${NEXTAUTH_SECRET}|g" .env
sed -i '' 's|^DATABASE_URL=.*|DATABASE_URL="file:./prisma/dev.db"|g' .env

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
