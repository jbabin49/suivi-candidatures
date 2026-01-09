# 📋 Suivi Candidatures

Application web moderne pour gérer vos candidatures d'emploi. Suivez l'état de vos candidatures, gérez vos rappels et organisez votre recherche d'emploi efficacement.

![Next.js](https://img.shields.io/badge/Next.js-15-black?style=flat-square&logo=next.js)
![React](https://img.shields.io/badge/React-19-blue?style=flat-square&logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-Strict-blue?style=flat-square&logo=typescript)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-CSS-38B2AC?style=flat-square&logo=tailwind-css)
![SQLite](https://img.shields.io/badge/SQLite-Prisma-003B57?style=flat-square&logo=sqlite)

---

## ✨ Fonctionnalités

### 🔐 Authentification
- Système de connexion sécurisé avec JWT
- Enregistrement public (self-service)
- Isolation des données par utilisateur
- Gestion du profil (changer username/mot de passe)

### 📊 Dashboard
- Vue d'ensemble avec statistiques
- Filtrage cliquable par statut (Postulées, Entretiens, Acceptées, Refusées)
- Liste des candidatures avec détails complets
- Rappels à venir

### 💼 Gestion des Candidatures
- ➕ Créer une candidature complète
- ✏️ Modifier les infos et rappels
- 🗑️ Supprimer une candidature
- 📎 Ajouter des documents (lettre de motivation, logo)

### 📝 Informations Détaillées
- Entreprise, poste, localisation
- Salaire, URL de l'offre
- Type de candidature (réponse/spontanée)
- Type de poste (emploi/stage)
- Type de contrat (CDI/CDD/Intérim)
- Email et téléphone de contact (au moins un requis)
- Notes personnelles

### ⏰ Rappels
- Créer des rappels pour chaque candidature
- Voir les 5 prochains rappels sur le dashboard
- Gérer les rappels lors de l'édition

### 🌙 Interface
- Design responsive (mobile/desktop)
- Mode clair et mode sombre
- Interface intuitive avec Tailwind CSS

---

## 🚀 Installation Rapide

### Windows
Double-cliquez sur `install-windows.bat` et suivez les instructions.

### Linux
```bash
chmod +x install-linux.sh
./install-linux.sh
```

### macOS
```bash
chmod +x install-macos.sh
./install-macos.sh
```

Pour plus de détails, consultez [INSTALLATION.md](./INSTALLATION.md)

---

## 🔧 Démarrage

```bash
# Mode développement
npm run dev

# Build pour production
npm run build

# Lancer en production
npm start

# Accéder à la base de données (GUI)
npx prisma studio
```

L'application sera disponible à [http://localhost:3000](http://localhost:3000)

### Identifiants par défaut
- **Username**: `admin`
- **Password**: `admin123`

⚠️ **Changez ces identifiants après la première connexion !**

---

## 📦 Stack Technologique

### Frontend
- **Next.js 15** - Framework React avec App Router
- **React 19** - UI components
- **TypeScript** - Type-safety
- **Tailwind CSS 3.4** - Styling
- **NextAuth.js 4.24** - Authentification

### Backend
- **Next.js API Routes** - Backend API
- **Prisma 5** - ORM type-safe
- **SQLite** - Base de données

### Sécurité
- **bcryptjs** - Hachage des mots de passe
- **NextAuth JWT** - Tokens JWT sécurisés
- **CSRF Protection** - Protection contre les attaques CSRF

---

## 🗂️ Structure du Projet

```
├── app/
│   ├── api/
│   │   ├── applications/        # API CRUD candidatures
│   │   ├── user/                # API utilisateur/profil
│   │   └── upload/              # API uploads fichiers
│   ├── dashboard/
│   │   ├── page.tsx             # Dashboard principal
│   │   ├── add/                 # Créer candidature
│   │   ├── edit/[id]/           # Éditer candidature
│   │   └── settings/            # Paramètres utilisateur
│   ├── login/                   # Page connexion
│   ├── register/                # Page inscription
│   └── layout.tsx               # Layout global
├── lib/
│   ├── auth.ts                  # Config NextAuth
│   └── prisma.ts                # Client Prisma
├── components/
│   └── LogoutButton.tsx         # Bouton déconnexion
├── prisma/
│   ├── schema.prisma            # Schéma base de données
│   └── dev.db                   # Base de données SQLite
├── public/
│   └── uploads/                 # Fichiers uploadés
├── .env.example                 # Variables d'env (template)
├── INSTALLATION.md              # Guide d'installation
└── package.json                 # Dépendances
```

---

## 🗄️ Schéma Base de Données

### User
```typescript
{
  id: string
  username: string (unique)
  password: string (bcrypt)
  createdAt: DateTime
  applications: Application[]
}
```

### Application
```typescript
{
  id: string
  company: string
  position: string
  status: "applied" | "interview" | "accepted" | "rejected"
  applicationDate: DateTime
  notes: string?
  contactEmail: string?
  contactPhone: string?
  salary: string?
  location: string?
  url: string?
  applicationType: "response" | "spontaneous"
  jobType: "job" | "internship"
  contractType: "cdi" | "cdd" | "interim"?
  coverLetterPath: string?
  companyLogoPath: string?
  userId: string
  reminders: Reminder[]
  createdAt: DateTime
  updatedAt: DateTime
}
```

### Reminder
```typescript
{
  id: string
  title: string
  date: DateTime
  completed: boolean
  applicationId: string
  createdAt: DateTime
}
```

---

## 🔌 API Endpoints

### Authentification
- `POST /api/auth/callback/credentials` - Connexion
- `GET/POST /api/auth/signout` - Déconnexion

### Candidatures
- `GET /api/applications` - Lister les candidatures
- `POST /api/applications` - Créer une candidature
- `GET /api/applications/[id]` - Récupérer une candidature
- `PUT /api/applications/[id]` - Mettre à jour une candidature
- `DELETE /api/applications/[id]` - Supprimer une candidature

### Utilisateur
- `POST /api/users` - Enregistrer (public)
- `GET /api/users` - Lister les utilisateurs (admin)
- `GET /api/user/profile` - Récupérer le profil
- `PUT /api/user/profile` - Mettre à jour le profil

### Fichiers
- `POST /api/upload` - Uploader un fichier

---

## 🔒 Sécurité

- ✅ Authentification JWT avec NextAuth.js
- ✅ Mots de passe hachés avec bcryptjs (10 salt rounds)
- ✅ Isolation des données par utilisateur
- ✅ CSRF protection automatique
- ✅ Vérification de propriété sur chaque requête
- ✅ Paramètres dynamiques awaités (Next.js 15)
- ✅ Validation côté serveur et client

---

## 🚀 Déploiement

### Prérequis Production
- Node.js 18+
- Base de données (SQLite local ou PostgreSQL)
- NEXTAUTH_SECRET généré sécurisé

### Déploiement Recommandé
- **Vercel** - Optimisé pour Next.js
- **Railway** - Support PostgreSQL
- **Netlify** - Alternative gratuite
- **VPS** - Contrôle total (DigitalOcean, Linode, etc.)

### Avant le Déploiement
```bash
# Générer un secret NextAuth
openssl rand -base64 32

# Ajouter à .env.production
NEXTAUTH_SECRET="votre-secret-genere"
NEXTAUTH_URL="https://votre-domaine.com"
DATABASE_URL="postgresql://..." # Si PostgreSQL

# Build et test
npm run build
npm start
```

---

## 📝 Variables d'Environnement

Créez un fichier `.env` basé sur `.env.example` :

```env
# Base de données
DATABASE_URL="file:./prisma/dev.db"

# NextAuth
NEXTAUTH_SECRET="secret-genere-avec-openssl"
NEXTAUTH_URL="http://localhost:3000"

# Environnement
NODE_ENV="development"
```

---

## 🛠️ Développement

### Scripts Disponibles

```bash
npm run dev        # Mode développement avec Turbopack
npm run build      # Build pour production
npm start          # Lancer build production
npm run lint       # Vérifier le code

# Prisma
npx prisma studio # GUI de la base de données
npx prisma migrate dev --name "nom"  # Créer une migration
npx prisma migrate reset  # Réinitialiser (⚠️ destructive)
```

### Générer une Migration

```bash
# Après modification de prisma/schema.prisma
npx prisma migrate dev --name "describe-changes"
```

---

## 🐛 Dépannage

### Port 3000 déjà utilisé
```bash
npm run dev -- -p 3001
```

### Erreur de base de données
```bash
npx prisma migrate reset  # Attention: supprime les données
```

### Erreurs TypeScript après Prisma
```bash
# Régénérer le client Prisma
npx prisma generate
```

### Sur Linux/macOS: Permission denied
```bash
chmod +x install-linux.sh
chmod +x install-macos.sh
```

---

## 📞 Support

Pour les questions ou problèmes:
1. Consultez le fichier [INSTALLATION.md](./INSTALLATION.md)
2. Vérifiez les logs dans le terminal
3. Vérifiez la console du navigateur (F12)
4. Vérifiez la base de données avec `npx prisma studio`

---

## 🐛 Signaler un Bug ou Demander une Fonctionnalité

Vous avez trouvé un bug ou vous avez une idée pour améliorer l'application ?

### 🐛 Signaler un Bug
Créez une **issue** sur GitHub avec :
- Description claire du problème
- Étapes pour reproduire
- Comportement attendu vs actuel
- Votre système d'exploitation et version Node.js

### ✨ Demander une Fonctionnalité
Créez une **issue** avec le tag `enhancement` incluant :
- Description de la fonctionnalité
- Cas d'usage
- Bénéfices

👉 [Créer une Issue](https://github.com/jbabin49/suivi-candidatures/issues/new)

---

## 📄 Licence

Ce projet est sous licence **MIT**. Vous êtes libre de l'utiliser, le modifier et le distribuer.

Consultez le fichier [LICENSE](./LICENSE) pour plus de détails.

---

**Version**: 1.0.0  
**Dernière mise à jour**: Janvier 2026