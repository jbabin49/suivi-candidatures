"""
Configuration de l'application, lue depuis les variables d'environnement
(fichier .env en developpement, variables du conteneur en production).

Un seul objet Settings, instancie une fois et importe partout. Les
valeurs par defaut permettent un lancement immediat en auth locale sans
aucune configuration.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mode d'authentification : "local" (comptes internes) ou "oidc".
    # Un seul mode actif par instance.
    auth_mode: str = "local"

    # Expose les pages de documentation generees par FastAPI : /docs,
    # /redoc et /openapi.json. L'application n'a pas d'API, tout est
    # rendu cote serveur ; ces pages decrivent neanmoins ses routes.
    # Desactivees par defaut, pour deux raisons : elles sont accessibles
    # sans authentification et publient la liste de toutes les routes et
    # de tous les champs de formulaire, et elles chargent leurs
    # ressources depuis un CDN, ce que la politique de securite du
    # contenu bloque. A n'activer qu'en developpement.
    enable_docs: bool = False

    # Cle de signature des cookies de session. A changer en production ;
    # une valeur aleatoire est generee au demarrage si laissee par defaut.
    secret_key: str = "change-me"

    # Flag Secure du cookie de session. Faux par defaut, pour ne pas
    # casser un acces en HTTP local : un cookie Secure est purement et
    # simplement ignore par le navigateur sur une origine http://.
    # A passer a true des que l'application est servie en HTTPS (reverse
    # proxy), sinon le cookie de session circule en clair.
    session_cookie_secure: bool = False

    # Duree de vie de la session, en secondes (defaut 12 heures).
    # La session est un cookie signe, sans etat cote serveur : elle ne
    # peut pas etre revoquee a distance, seule la rotation de
    # data/secret.key invalide les cookies emis. D'ou une duree courte,
    # bien plus courte que les 14 jours par defaut de Starlette.
    session_max_age: int = 12 * 60 * 60

    # Dossier des donnees persistantes (volume Docker). Contient la base
    # SQLite et le sous-dossier uploads.
    data_dir: Path = Path("data")

    # Taille maximale d'un fichier televerse, en octets (defaut 10 Mo).
    max_upload_bytes: int = 10 * 1024 * 1024

    # Extensions autorisees au televersement, separees par des virgules.
    # Liste blanche volontairement restrictive : un .html ou un .svg
    # televerse puis consulte s'executerait dans l'origine de
    # l'application (XSS stockee).
    upload_extensions: str = "pdf,doc,docx,odt,png,jpg,jpeg,webp"

    # Compte administrateur cree automatiquement au premier demarrage
    # en mode local, s'il n'existe aucun utilisateur. Laisser vide pour
    # creer le compte manuellement (script creer_utilisateur.py).
    admin_email: str | None = None
    admin_password: str | None = None

    # Parametres OIDC, utilises uniquement si auth_mode == "oidc".
    oidc_issuer_url: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None

    @property
    def extensions_autorisees(self) -> frozenset[str]:
        """
        Extensions autorisees, normalisees avec le point initial et en
        minuscules, pour comparaison directe avec Path(...).suffix.
        """
        return frozenset(
            "." + element.strip().lstrip(".").lower()
            for element in self.upload_extensions.split(",")
            if element.strip()
        )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "candidatures.db"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"


@lru_cache
def get_settings() -> Settings:
    """
    Retourne l'instance unique de configuration. lru_cache garantit
    qu'elle n'est lue qu'une fois.
    """
    settings = Settings()
    # Cree l'arborescence des donnees si absente (premier lancement).
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    return settings
