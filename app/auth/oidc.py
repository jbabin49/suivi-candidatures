"""
Authentification externe OIDC (OpenID Connect).

Actif lorsque AUTH_MODE=oidc. L'application agit comme client OIDC :
elle redirige l'utilisateur vers le fournisseur d'identite (Authelia,
Authentik, Keycloak, Pocket ID, Zitadel...), qui le renvoie apres
connexion. L'application ne gere ni mot de passe ni interface de login
dans ce mode, elle fait confiance a l'identite fournie.

Le fournisseur est decrit par trois parametres de config :
oidc_issuer_url, oidc_client_id, oidc_client_secret. La decouverte des
points d'acces (autorisation, jeton, cles) se fait automatiquement via
l'URL de decouverte standard du fournisseur.
"""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User
from app.session import login_user, logout_user

router = APIRouter(tags=["auth"])
settings = get_settings()

# Enregistrement du fournisseur OIDC. server_metadata_url pointe vers le
# document de decouverte standard, authlib en deduit tous les points
# d'acces et les cles de signature.
oauth = OAuth()
if settings.auth_mode == "oidc" and settings.oidc_issuer_url:
    oauth.register(
        name="oidc",
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        server_metadata_url=(
            settings.oidc_issuer_url.rstrip("/")
            + "/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid email profile"},
    )


@router.get("/login")
async def login(request: Request):
    """
    Point d'entree de la connexion OIDC : redirige vers le fournisseur
    d'identite. Le callback (redirect_uri) revient sur /auth/callback.
    """
    redirect_uri = request.url_for("auth_callback")
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """
    Retour du fournisseur apres connexion. Recupere le jeton, en extrait
    l'identite (sujet et email), puis cree ou retrouve le compte local
    correspondant et ouvre la session.
    """
    try:
        token = await oauth.oidc.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Echec de l'authentification OIDC",
        )

    claims = token.get("userinfo") or {}
    subject = claims.get("sub")
    email = claims.get("email")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reponse OIDC incomplete",
        )

    user = get_or_create_user(db, subject=subject, email=email, claims=claims)
    login_user(request, user)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(request: Request):
    """
    Deconnexion locale (vide la session de l'application). La session chez
    le fournisseur d'identite n'est pas touchee ; une deconnexion globale
    SSO depasse le cadre de cette v1.
    """
    logout_user(request)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


def get_or_create_user(
    db: Session, subject: str, email: str | None, claims: dict
) -> User:
    """
    Retrouve le compte par son sujet OIDC, ou le cree au premier login
    (provisionnement automatique). Le sujet est l'identifiant stable ;
    l'email peut changer cote fournisseur sans casser le rattachement.
    """
    user = db.scalar(select(User).where(User.oidc_subject == subject))
    if user is not None:
        return user

    nom = claims.get("name") or email or subject
    user = User(
        email=email or f"{subject}@oidc.local",
        nom_affichage=nom,
        oidc_subject=subject,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
