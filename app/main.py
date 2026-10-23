"""
Point d'entree de l'application FastAPI.

Au demarrage :
- resolution de la cle de signature des sessions (voir resolve_secret_key),
- creation des tables si absentes,
- montage des fichiers statiques et des routes.

Le mode d'authentification (AUTH_MODE) decide quelles routes d'auth sont
montees : "local" monte le formulaire de connexion et la verification de
mot de passe ; "oidc" monte le flux de redirection vers le fournisseur
d'identite.

Lancement en developpement (depuis la racine du projet) :
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import init_db
from app.routes import (
    candidatures,
    contacts,
    documents,
    entretiens,
    export,
    profil,
    relances,
)
from app.session import get_optional_user

settings = get_settings()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def resolve_secret_key() -> str:
    """
    Determine la cle de signature des sessions, par ordre de priorite :

    1. Valeur explicite du .env (si differente du placeholder "change-me").
    2. Cle persistee dans data/secret.key, relue si le fichier existe.
    3. Sinon, generation d'une cle aleatoire ecrite dans data/secret.key.

    Persister la cle dans data/ la garde stable entre redemarrages (pas de
    deconnexion a chaque restart) et l'inclut dans la sauvegarde du volume :
    une restauration de data/ suffit, sans reconfiguration.
    """
    if settings.secret_key and settings.secret_key != "change-me":
        return settings.secret_key

    key_file = settings.data_dir / "secret.key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()

    key = secrets.token_urlsafe(64)
    key_file.write_text(key, encoding="utf-8")
    key_file.chmod(0o600)  # lecture/ecriture reservees au proprietaire
    return key


def _bootstrap_admin() -> None:
    """
    En mode local, cree le compte administrateur defini par ADMIN_EMAIL /
    ADMIN_PASSWORD s'il n'existe encore aucun utilisateur. Sans ces
    variables, aucun compte n'est cree : utiliser alors le script
    creer_utilisateur.py.
    """
    if settings.auth_mode != "local":
        return
    if not settings.admin_email or not settings.admin_password:
        return

    from sqlalchemy import select

    from app.auth.local import hash_password
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        existe = db.scalar(select(User.id).limit(1))
        if existe is None:
            db.add(
                User(
                    email=settings.admin_email,
                    nom_affichage=settings.admin_email,
                    password_hash=hash_password(settings.admin_password),
                )
            )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _bootstrap_admin()
    yield


app = FastAPI(
    title="Suivi de candidatures",
    lifespan=lifespan,
    # Documentation interactive desactivee par defaut (voir ENABLE_DOCS).
    # Passer les URL a None retire completement les routes, elles ne sont
    # pas seulement protegees.
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=resolve_secret_key(),
    max_age=settings.session_max_age,
    # same_site="lax" est deja le defaut de Starlette, mais il est pose
    # explicitement ici : c'est la seule protection anti-CSRF de
    # l'application, puisqu'il n'y a pas de jeton par formulaire. Un
    # navigateur n'envoie pas un cookie Lax sur une requete POST
    # provenant d'un autre site.
    same_site="lax",
    # Ajoute le flag Secure au cookie. Voir SESSION_COOKIE_SECURE.
    https_only=settings.session_cookie_secure,
)


# Politique de securite du contenu.
#
# L'application ne charge que ses propres ressources : aucun CDN, aucune
# police distante, aucune image externe, aucun appel reseau depuis le
# JavaScript. script-src peut donc rester en 'self' strict, sans
# 'unsafe-inline' : les trois comportements qui etaient inline (init du
# theme, lignes de tableau cliquables, confirmation de suppression) ont
# ete externalises dans static/js/theme-init.js et
# static/js/interactions.js.
#
# Seule concession : style-src-attr 'unsafe-inline', pour les attributs
# style="..." cosmetiques encore presents dans les gabarits. Les blocs
# <style> et les feuilles distantes restent interdits. A supprimer si ces
# attributs sont un jour convertis en classes CSS.
#
# Les donnees de la frise chronologique passent par un attribut data-*
# (voir candidature.html) et non par un bloc <script type="application/
# json"> : Firefox applique script-src-elem a tout element <script>
# porteur de contenu inline, quel que soit son type.
CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "style-src-attr 'unsafe-inline'",
        "img-src 'self'",
        "font-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

# Nom de l'en-tete CSP a emettre.
#
# Mode bloquant, valide le 23 octobre 2026 : parcours complet verifie en
# navigation privee (connexion, accueil et lignes cliquables, detail et
# frise, confirmation de suppression, bascule de theme), sans aucune
# violation signalee.
#
# Pour diagnostiquer une regression sans rien casser, repasser
# temporairement en Report-Only en echangeant les deux lignes.
EN_TETE_CSP = "Content-Security-Policy"
# EN_TETE_CSP = "Content-Security-Policy-Report-Only"


@app.middleware("http")
async def entetes_de_securite(request: Request, call_next):
    """
    Pose les en-tetes de securite sur toutes les reponses.

    setdefault et non affectation directe : une route qui a deja pose
    l'un de ces en-tetes garde sa valeur. C'est le cas de la consultation
    d'un document, qui impose son propre X-Content-Type-Options.
    """
    reponse = await call_next(request)
    reponse.headers.setdefault(EN_TETE_CSP, CSP)
    reponse.headers.setdefault("X-Content-Type-Options", "nosniff")
    # no-referrer : les gabarits contiennent des liens sortants (lien
    # d'annonce, page d'un contact), aucune URL interne ne doit fuiter.
    reponse.headers.setdefault("Referrer-Policy", "no-referrer")
    return reponse


@app.exception_handler(401)
async def redirige_vers_login(request: Request, exc):
    """
    Sur une requete de navigateur (qui attend du HTML) non authentifiee,
    rediriger vers la page de connexion plutot que renvoyer un JSON 401
    brut. Les appels attendant du JSON (API, export) gardent le 401.
    """
    from fastapi.responses import JSONResponse

    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return RedirectResponse(url="/login", status_code=303)
    return JSONResponse(status_code=401, content={"detail": str(exc.detail)})


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Routes fonctionnelles (communes aux deux modes d'auth).
app.include_router(candidatures.router)
app.include_router(relances.router)
app.include_router(contacts.router)
app.include_router(entretiens.router)
app.include_router(documents.router)
app.include_router(profil.router)
app.include_router(export.router)

# Routes d'authentification, selon le mode actif.
if settings.auth_mode == "oidc":
    from app.auth import oidc

    app.include_router(oidc.router)
else:
    from app.auth import local

    app.include_router(local.router)

    @app.get("/login", response_class=HTMLResponse)
    def page_login(request: Request, user=Depends(get_optional_user)):
        """Affiche le formulaire de connexion (ou redirige si deja connecte)."""
        if user is not None:
            return RedirectResponse(url="/")
        return templates.TemplateResponse(request, "login.html", {})


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Verification de disponibilite (utile pour Docker et le reverse proxy)."""
    return {"status": "ok"}
