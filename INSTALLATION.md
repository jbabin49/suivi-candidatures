# Guide d'Installation - Suivi Candidatures

## Prérequis Minimums

- **Node.js** 18.x ou supérieur (recommandé: 20.x LTS)
- **npm** 9.x ou supérieur (inclus avec Node.js)
- **SQLite3** (intégré à Prisma, pas d'installation supplémentaire requise)

## Installation Rapide

### Windows

1. **Téléchargez Node.js**
   - Visitez [nodejs.org](https://nodejs.org/)
   - Téléchargez la version LTS
   - Installez en gardant les paramètres par défaut
   - Redémarrez votre ordinateur

2. **Lancez le script d'installation**
   - Double-cliquez sur `install-windows.bat`
   - Attendez que l'installation se termine

3. **Démarrer l'application**
   ```bash
   npm run dev
   ```
   - Accédez à http://localhost:3000

---

### Linux (Ubuntu/Debian)

```bash
# Rendre le script exécutable
chmod +x install-linux.sh

# Lancer l'installation
./install-linux.sh

# Démarrer l'application
npm run dev
```

**Pour d'autres distributions (Fedora, Arch, etc.):**
- Le script détecte automatiquement votre distribution
- Assurez-vous que `sudo` est disponible pour installer les packages

---

### macOS

```bash
# Rendre le script exécutable
chmod +x install-macos.sh

# Lancer l'installation
./install-macos.sh

# Démarrer l'application
npm run dev
```

**Prérequis:**
- Homebrew sera installé automatiquement si nécessaire

---

## Ce que font les scripts d'installation

✓ Vérifie l'installation de Node.js et npm  
✓ Installe les packages npm  
✓ Configure la base de données SQLite  
✓ Crée un utilisateur par défaut (admin/admin123)  

---

## Accès à l'Application

- **URL:** http://localhost:3000
- **Utilisateur par défaut:** `admin`
- **Mot de passe par défaut:** `admin123`

### Première connexion
1. Connectez-vous avec les credentials par défaut
2. Cliquez sur "S'inscrire" pour créer d'autres comptes utilisateurs
3. Commencez à gérer vos candidatures!

---

## Commandes Utiles

```bash
# Démarrer en mode développement
npm run dev

# Build pour la production
npm run build

# Lancer la version production
npm start

# Accéder à la base de données (GUI)
npx prisma studio

# Réinitialiser la base de données (⚠️ destructive)
npx prisma migrate reset
```

---

## Dépannage

### "Node.js n'est pas installé"
- Téléchargez depuis [nodejs.org](https://nodejs.org/)
- Assurez-vous de redémarrer après l'installation

### "Port 3000 déjà utilisé"
Changez le port:
```bash
npm run dev -- -p 3001
```
Puis accédez à http://localhost:3001

### "Erreur de base de données"
Réinitialisez la base de données:
```bash
npx prisma migrate reset
```

### Sur Linux/macOS: Permission denied
```bash
chmod +x install-linux.sh
# ou
chmod +x install-macos.sh
```

---

## Configuration Avancée

### Variables d'Environnement

Créez un fichier `.env.local` à la racine:

```env
# Base de données (défaut: file:./prisma/dev.db)
DATABASE_URL="file:./prisma/dev.db"

# NextAuth Secret (générez avec: openssl rand -base64 32)
NEXTAUTH_SECRET="votre-secret-genere"

# URL du site (pour CSRF en production)
NEXTAUTH_URL="http://localhost:3000"
```

---

## Architecture

- **Frontend:** Next.js 15 + React 19 + Tailwind CSS
- **Backend:** Next.js API Routes + Prisma 5
- **Base de données:** SQLite (fichier `prisma/dev.db`)
- **Authentification:** NextAuth.js avec JWT

---

## Support

Pour plus d'informations:
- Consultez le README.md à la racine du projet
- Vérifiez les logs dans le terminal lors du démarrage
- Vérifiez les erreurs dans la console du navigateur (F12)

---

Bonne installation! 🚀
