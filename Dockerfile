# Image de l'application. Base Python mince (slim) pour rester legere.
FROM python:3.12-slim

# Variables d'environnement Python : pas de .pyc, sortie non bufferisee
# (logs visibles immediatement dans docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Utilisateur non privilegie, cree avant l'installation pour profiter du
# cache. UID et GID 1000 volontairement : c'est l'identifiant du premier
# compte utilisateur sur la quasi-totalite des distributions Linux, donc
# les fichiers ecrits dans le volume monte depuis l'hote appartiennent a
# ce compte et restent lisibles et sauvegardables sans sudo.
#
# Si votre compte hote n'est pas en 1000, surcharger a l'execution :
#     user: "${UID}:${GID}"      (docker compose)
#     --user "$(id -u):$(id -g)" (docker run)
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin app

WORKDIR /app

# Installation des dependances en premier, pour profiter du cache Docker :
# tant que requirements.txt ne change pas, cette couche n'est pas rejouee.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code applicatif. Il reste la propriete de root : l'utilisateur
# applicatif peut le lire et l'executer, mais pas le modifier.
COPY app/ ./app/

# Outils d'exploitation de la racine, utilisables via :
#     docker compose exec app python creer_utilisateur.py <email> "<Nom>"
# Motif glob plutot qu'une liste explicite, pour ne pas faire echouer la
# construction si l'un de ces scripts optionnels est absent.
COPY *.py ./

# Donnees et scripts de demonstration (jeu fictif pour les captures et la
# contribution), utilisables via :
#     docker compose exec app python donnees_demo/seed_demo.py
COPY donnees_demo/ ./donnees_demo/

# Normalisation des permissions de lecture. COPY preserve les modes du
# poste de build, ou plusieurs sources sont en 0600 : sans ce chmod,
# l'utilisateur non privilegie ne pourrait pas lire son propre code.
# a+rX ajoute la lecture pour tous, et le parcours sur les dossiers
# seulement. L'ecriture reste reservee a root.
RUN chmod -R a+rX /app/app /app/donnees_demo /app/requirements.txt \
    && chmod a+r /app/*.py

# Dossier des donnees persistantes. Cree et attribue a l'utilisateur
# applicatif AVANT la declaration du volume, pour qu'un volume Docker
# anonyme ou nomme herite de cette appartenance. Avec un montage lie
# (bind mount), c'est l'appartenance cote hote qui s'applique : voir le
# README pour la reprise d'une installation anterieure.
RUN mkdir -p /app/data/uploads && chown -R app:app /app/data

VOLUME ["/app/data"]

EXPOSE 8000

# Tout ce qui suit, et le processus applicatif, tournent sans privileges.
USER app

# Lancement via uvicorn. Un seul worker : SQLite n'aime pas les ecritures
# concurrentes multi-process, et un worker suffit pour cet usage.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
