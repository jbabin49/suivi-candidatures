# -*- mode: python ; coding: utf-8 -*-
"""
Specification PyInstaller de la version de bureau (desktop.py).

Produit un executable autonome non signe, un par systeme : le .spec est
le meme partout, mais PyInstaller ne croise pas les plateformes, chaque
binaire doit etre construit sur l'OS cible (voir BUILD.md).

    pyinstaller suivi-candidatures.spec

Trois points demandent une declaration explicite, PyInstaller ne les
decouvrant pas par analyse statique :

1. Les ressources non-Python (gabarits, CSS/JS, alembic.ini, scripts de
   migration) : rien dans le code ne les importe, elles sont lues par
   chemin a l'execution. Sans migrations/, l'upgrade Alembic lance au
   demarrage par init_db() echoue des le premier lancement.
2. Les modules charges dynamiquement par uvicorn (implementations de
   protocole HTTP et de boucle d'evenements, resolues par nom au
   demarrage) et les backends de argon2 et anyio.
3. Les scripts de migrations/versions, embarques comme donnees et non
   comme modules : migrations/ n'est pas un paquet Python (pas de
   __init__.py), et alembic charge env.py et chaque revision depuis le
   chemin de script_location. Leurs propres imports (alembic, sqlalchemy)
   sont deja embarques par ailleurs, l'analyse de ces fichiers n'apporte
   donc rien.
"""

from PyInstaller.utils.hooks import collect_submodules

NOM = "SuiviCandidatures"

# Ressources lues par chemin a l'execution. Destination relative a la
# racine du bundle (sys._MEIPASS), que app/database.py prend pour racine
# quand sys.frozen est vrai.
datas = [
    ("app/templates", "app/templates"),
    ("app/static", "app/static"),
    ("alembic.ini", "."),
    ("migrations", "migrations"),
]

hiddenimports = [
    # uvicorn[standard] : httptools, websockets, uvloop et les classes
    # de protocole sont designees par chaine de caracteres dans la
    # configuration, donc invisibles a l'analyse des imports.
    *collect_submodules("uvicorn"),
    # anyio choisit son backend (asyncio) par nom au premier appel.
    *collect_submodules("anyio"),
    # argon2-cffi charge sa liaison native et ses profils de parametres.
    *collect_submodules("argon2"),
    # alembic resout ses operations de migration (op.create_table...)
    # et ses dialectes par nom.
    *collect_submodules("alembic"),
]

a = Analysis(
    ["desktop.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name=NOM,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Fenetre pywebview, pas de console : rien n'est saisi au clavier
    # dans un terminal, et une console noire au lancement fait peur.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    # Ni signature ni notarisation : release publique non signee, voir le
    # parcours de premier lancement par OS dans le README.
    codesign_identity=None,
    entitlements_file=None,
)

# Bundle .app sous macOS : un executable nu y est lancable mais n'a ni
# icone dans le Dock ni nom de fenetre correct. PyInstaller ignore ce
# bloc sur les autres plateformes.
app = BUNDLE(
    exe,
    name=f"{NOM}.app",
    icon=None,
    bundle_identifier=None,
)
