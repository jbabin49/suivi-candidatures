# Construction de la version de bureau

Ce document décrit la fabrication des exécutables autonomes de la version de
bureau (`desktop.py`), celle qui s'utilise sans Docker et sans navigateur.

Pour l'installation et le premier lancement côté utilisateur, voir la section
« Installation (version de bureau) » du [README](README.md).

## Cibles

Deux exécutables seulement, **Windows et macOS**.

| Système | Binaire publié | Comment l'utiliser |
| --- | --- | --- |
| Windows 10/11 | `SuiviCandidatures-windows.exe` | exécutable autonome |
| macOS | `SuiviCandidatures-macos.zip` (`.app`) | **Apple Silicon uniquement** |
| Linux | *aucun* | Docker, ou `python desktop.py` |

### Pas de binaire Linux, délibérément

L'application est déjà distribuée sous Linux par son image Docker, et la version
de bureau y démarre directement depuis les sources. Empaqueter en plus un binaire
PyInstaller obligerait à embarquer ou à exiger WebKitGTK — dont le nom de paquet
change selon la distribution et selon la version (`4.0` retiré d'Ubuntu 24.04 au
profit de `4.1`, nommage encore différent sur Arch et Fedora) — pour un gain nul
face aux deux voies qui existent déjà.

Les deux manières d'utiliser l'application sous Linux :

```bash
# 1. Docker, le déploiement normal
docker compose up -d        # puis http://localhost:8000

# 2. Fenêtre de bureau depuis les sources
pip install -r requirements-desktop.txt
python desktop.py
```

La seconde voie demande WebKitGTK sur le système, que `pywebview` utilise comme
moteur de rendu :

```bash
# Debian / Ubuntu 24.04 et suivants (série 4.1 ; la 4.0 a été retirée)
sudo apt-get install -y gir1.2-gtk-3.0 gir1.2-webkit2-4.1 python3-gi python3-gi-cairo
# Arch
sudo pacman -S --needed gtk3 webkit2gtk-4.1 python-gobject
# Fedora
sudo dnf install gtk3 webkit2gtk4.1 python3-gobject
```

En cas d'erreur `Namespace WebKit2 not available`, c'est le paquet
`gir1.2-webkit2-4.1` (ou son équivalent) qui manque.

## Principe

Un seul fichier de spécification, [suivi-candidatures.spec](suivi-candidatures.spec),
sert pour les deux systèmes. PyInstaller ne sait pas construire pour une autre
plateforme que la sienne : **un binaire par système, construit sur ce système**.
C'est le rôle de la matrice du workflow
[.github/workflows/release.yml](.github/workflows/release.yml), qui fait
exactement, sur chaque *runner*, ce qui est décrit ci-dessous.

Les binaires produits ne sont **ni signés ni notarisés**. Aucun certificat
Apple ni Authenticode n'est nécessaire pour construire, et aucun secret de
signature n'est stocké dans le dépôt. En contrepartie, l'utilisateur doit
contourner un avertissement au premier lancement (voir le README).

## Dépendances

Les dépendances Python sont dans [requirements-desktop.txt](requirements-desktop.txt),
qui inclut `requirements.txt`. S'y ajoute PyInstaller, outil de build et non
dépendance d'exécution, donc volontairement absent de ce fichier.

```bash
pip install -r requirements-desktop.txt
pip install pyinstaller
```

Aucune dépendance système à installer sur les deux cibles : `pywebview` s'appuie
sur le moteur de rendu fourni par l'OS.

| Système | Moteur de rendu | À installer |
| --- | --- | --- |
| Windows 10/11 | WebView2 | rien (présent par défaut) |
| macOS | WebKit | rien (fourni par le système) |

## Commande de build

Identique sur les deux systèmes :

```bash
pyinstaller --noconfirm --clean suivi-candidatures.spec
```

Résultat dans `dist/` :

| Système | Sortie | Architecture |
| --- | --- | --- |
| Windows | `dist/SuiviCandidatures.exe` | celle de la machine de build (`x86_64` en CI) |
| macOS | `dist/SuiviCandidatures.app` (et l'exécutable nu `dist/SuiviCandidatures`) | **`arm64` seulement** |

PyInstaller produit un binaire pour l'architecture de la machine qui construit.
Le runner `macos-latest` est une machine Apple Silicon : le `.app` publié est
donc **`arm64` seul et ne démarre pas sur un Mac Intel**. C'est un choix assumé
— pas de build `universal2`, pas de runner Intel supplémentaire — simplement
documenté dans le README et dans le corps de la release. Un utilisateur sur Mac
Intel lance la version de bureau depuis les sources (`python desktop.py`), ou
construit lui-même sur sa machine avec la commande ci-dessus.

Sous macOS, c'est le `.app` qu'il faut distribuer, compressé avec `ditto` et non
avec `zip` — `ditto` préserve les liens symboliques et les attributs étendus du
bundle :

```bash
ditto -c -k --sequesterRsrc --keepParent \
  dist/SuiviCandidatures.app dist/SuiviCandidatures-macos.zip
```

## Ce que la spécification doit déclarer explicitement

PyInstaller trouve les dépendances en analysant les `import` du code. Trois
catégories de choses lui échappent, et sont donc déclarées à la main dans le
`.spec`. Chacune correspond à une panne observable au lancement.

**1. Les ressources lues par chemin** (`datas`) : gabarits Jinja2, CSS et
JavaScript, `alembic.ini`, et le dossier `migrations/`. Rien ne les importe,
elles sont ouvertes par nom de fichier à l'exécution. Oublier `migrations/` est
la panne la plus traître : `init_db()` applique un `alembic upgrade head` au
démarrage, qui échoue faute de scripts de migration — donc dès le premier
lancement, sur une base vide.

**2. Les modules résolus par nom** (`hiddenimports`) : `uvicorn` désigne ses
implémentations de protocole HTTP et sa boucle d'événements par chaîne de
caractères (`httptools`, `websockets`, `uvloop`), invisibles à l'analyse
statique. Même logique pour le backend d'`anyio` et la liaison native
d'`argon2`. D'où les `collect_submodules()` du `.spec`.

**3. La résolution des chemins Alembic sous bundle.** Dans un exécutable gelé,
`app/` vit à l'intérieur de l'archive du binaire : les fichiers de données sont
extraits dans un dossier temporaire désigné par `sys._MEIPASS`. Et le répertoire
courant d'une application lancée depuis le Finder ou le menu Démarrer est
imprévisible, alors qu'Alembic résout `script_location` relativement à lui.
[app/database.py](app/database.py) traite les deux cas : quand `sys.frozen` est
vrai, `alembic.ini` et `script_location` sont calculés en chemins **absolus**
depuis `sys._MEIPASS`. En exécution normale, la racine du projet reste utilisée,
rien ne change pour le développement ni pour les tests.

## Vérifier un build

Le test [tests/test_desktop_boot.py](tests/test_desktop_boot.py) couvre le
démarrage côté source (serveur en thread, `/healthz`, base créée dans un
`DATA_DIR` redirigé), sans jamais importer `webview` : il tourne donc en CI,
sans affichage.

Un binaire fraîchement construit se vérifie en revanche à la main, puisque la
fenêtre native est tout l'objet de l'exercice. Points à contrôler au premier
lancement :

- la fenêtre s'ouvre et affiche l'écran **Bienvenue** (création du premier
  compte) — s'il affiche `/login`, un compte existe déjà dans le `DATA_DIR` ;
- un identifiant et un mot de passe suffisent : le nom affiché est facultatif ;
- après création du compte, l'accueil s'affiche et la navigation fonctionne,
  **Comptes** et **Mot de passe** compris ;
- le dossier de données a bien été créé à l'emplacement standard de l'OS :

| Système | Emplacement de `DATA_DIR` |
| --- | --- |
| Windows | `%LOCALAPPDATA%\SuiviCandidatures` |
| macOS | `~/Library/Application Support/SuiviCandidatures` |
| Linux (depuis les sources) | `~/.local/share/SuiviCandidatures` |

C'est là que vivent la base `candidatures.db`, le dossier `uploads/` et
`secret.key` : **c'est le dossier à sauvegarder**, et le seul à supprimer pour
repartir de zéro.

## Éprouver la chaîne de build sans publier

Le workflow accepte un déclenchement manuel (`workflow_dispatch`) : onglet
**Actions > Release de bureau > Run workflow**, en choisissant la branche.

Le job de build est le même que pour un tag, mais le job de publication est
sauté — il est conditionné à `startsWith(github.ref, 'refs/tags/')`. **Aucune
Release publique n'est créée.** Les deux binaires sont récupérables dans la
section *Artifacts* de la page du run, le temps de la rétention configurée sur
le dépôt.

C'est la façon de vérifier que le `.spec` embarque bien tout ce qu'il faut —
notamment `migrations/` et les imports cachés — avant de poser un tag.

## Publier une release

Le workflow se déclenche sur un tag `v*` :

```bash
git tag v2.0.0
git push origin v2.0.0
```

Il construit les deux binaires, les téléverse comme artefacts, puis crée la
GitHub Release du tag en y attachant les deux fichiers.
