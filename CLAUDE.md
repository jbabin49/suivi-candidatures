# CLAUDE.md

Instructions pour les contributeurs (humains et agents) de ce dépôt.

## Résumé du projet

Application web **auto-hébergée de suivi de candidatures** : tableau de bord,
relances, contacts, entretiens, documents et frise chronologique par
candidature. Usage solo ou à quelques personnes.

- **Python 3.12 / FastAPI / SQLAlchemy**, base **SQLite** en mode WAL
- Gabarits **Jinja2** rendus côté serveur, **JavaScript vanilla** (frise SVG)
- Déploiement **Docker** (`docker compose up -d`)
- Authentification **locale (argon2)** ou **OIDC**, au choix via `AUTH_MODE`

## Règles non négociables

- **Aucune donnée réelle ou personnelle dans le dépôt**, captures d'écran
  comprises. Utiliser le jeu fictif de `donnees_demo/`.
- **Lire [SECURITE.md](SECURITE.md) avant de toucher** à l'authentification, au
  téléversement de fichiers ou aux gabarits.
- **Jamais de `| safe`** dans un gabarit Jinja2 sans échappement explicite en
  amont : c'est la protection contre le XSS stocké.
- **Respecter les versions figées de `requirements.txt`** (notamment
  SQLAlchemy 2.0.x et httpx 0.28.x). Pas de montée de version majeure au détour
  d'un correctif : ces migrations se traitent séparément.
- **Conteneur non-root** (uid/gid 1000). Ne rien introduire qui exige `root` à
  l'exécution.

## Tests avant commit

```bash
pip install pytest
pytest
```

Ou la version conteneurisée Python 3.12 (même version que l'image), déjà
documentée dans le README :

```bash
docker run --rm -v "$PWD":/src:ro -w /w python:3.12-slim sh -c \
  'cp -r /src/. /w/ && pip install -q -r requirements.txt pytest && pytest -q'
```

Les tests tournent sur une **base SQLite temporaire isolée** (voir
[tests/conftest.py](tests/conftest.py), qui fixe `DATA_DIR` et `AUTH_MODE`
avant tout import de l'application). Ne pas écrire de test qui dépende d'un
`.env` ou d'une base existante.

## Contrôle sécurité avant publication

```bash
trivy fs .
trivy config .
```

Objectif : **0 vulnérabilité / 0 secret / 0 misconfiguration bloquante**.

## Structure du projet

```
app/
  main.py            Point d'entrée, montage des routes
  config.py          Configuration (.env)
  database.py        Connexion SQLite (WAL)
  models.py          Tables SQLAlchemy
  schemas.py         Modèles Pydantic
  session.py         Session et utilisateur courant
  auth/              Authentification locale et OIDC
  routes/            Routes HTTP (candidatures, relances, contacts...)
  services/          Logique métier (timeline, stats, calcul des relances)
  templates/         Gabarits Jinja2
  static/            CSS et JavaScript
creer_utilisateur.py Création d'un compte en ligne de commande
donnees_demo/        Jeu de données fictif (démo, captures, contribution)
data/                Données persistantes (volume) - non versionné
tests/               Tests
```

## Points d'attention

- **SQLite mono-worker** : un seul worker uvicorn, SQLite supporte mal les
  écritures concurrentes multi-process. Ne pas passer en multi-worker sans
  revoir la concurrence d'accès à la base.
- **Durcissements restants avant une exposition sur Internet** :
  - *rate limiting* sur `POST /login` — **priorité** ;
  - invalidation de session côté serveur (la session est aujourd'hui un cookie
    signé sans état serveur, donc non révocable à distance) ;
  - filtre d'accès OIDC (restreindre qui peut se connecter via le fournisseur) ;
  - **migrations Alembic avant toute évolution du schéma** (le schéma est
    actuellement créé automatiquement au démarrage, sans migrations).
