"""
Validation et enregistrement des fichiers televerses.

Mutualise la logique qui etait dupliquee entre les routes documents et
profil (meme boucle d'ecriture, meme nommage, meme plafond de taille).

Trois regles de securite sont portees ici :

- seules les extensions de la liste blanche (UPLOAD_EXTENSIONS) sont
  acceptees, et le controle a lieu avant toute ecriture sur disque. Sans
  ce filtre, un .html ou un .svg televerse puis consulte s'executerait
  dans l'origine de l'application (XSS stockee).
- le type MIME est redetermine cote serveur a partir de l'extension
  validee. Celui annonce par le client n'est ni conserve ni reutilise.
- le nom de stockage est un UUID, jamais le nom fourni par le client.
  L'extension validee est seule conservee, et elle ne peut pas contenir
  de separateur de chemin (Path.suffix ne porte que sur le dernier
  composant), ce qui exclut toute traversee de repertoire.
"""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings

settings = get_settings()


def dossier_cible(user_id: int, candidature_id: int | None) -> Path:
    """
    Chemin du dossier de stockage, relatif a uploads/. Les documents de
    profil (sans candidature) vont dans un sous-dossier "profil".
    """
    sous = str(candidature_id) if candidature_id is not None else "profil"
    return Path(str(user_id)) / sous


def valider_extension(nom_fichier: str | None) -> str:
    """
    Retourne l'extension normalisee (point inclus, en minuscules) si elle
    figure dans la liste blanche. Leve une 400 explicite sinon.
    """
    extension = Path(nom_fichier or "").suffix.lower()
    autorisees = settings.extensions_autorisees
    if extension not in autorisees:
        acceptees = ", ".join(sorted(e.lstrip(".") for e in autorisees))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Extension de fichier non autorisee : "
                f"{extension or '(aucune)'}. Formats acceptes : {acceptees}."
            ),
        )
    return extension


def mime_depuis_extension(extension: str) -> str:
    """
    Type MIME deduit de l'extension cote serveur. Le type annonce par le
    client n'est pas fiable et n'est jamais utilise. La valeur retournee
    est purement informative : la consultation d'un document force de
    toute facon application/octet-stream.
    """
    devine, _ = mimetypes.guess_type(f"fichier{extension}")
    return devine or "application/octet-stream"


def enregistrer(fichier: UploadFile, dossier_rel: Path) -> tuple[str, int, str]:
    """
    Valide puis ecrit le fichier televerse sous un nom unique dans
    uploads/<dossier_rel>.

    Retourne (chemin relatif a stocker en base, taille en octets, type
    MIME determine cote serveur). Refuse les extensions hors liste
    blanche et les fichiers depassant la taille maximale configuree.
    """
    extension = valider_extension(fichier.filename)

    dossier_abs = settings.uploads_dir / dossier_rel
    dossier_abs.mkdir(parents=True, exist_ok=True)

    # Nom unique pour eviter toute collision, extension validee conservee.
    nom_stocke = f"{uuid.uuid4().hex}{extension}"
    chemin_abs = dossier_abs / nom_stocke

    taille = 0
    with chemin_abs.open("wb") as sortie:
        while chunk := fichier.file.read(1024 * 1024):
            taille += len(chunk)
            if taille > settings.max_upload_bytes:
                sortie.close()
                chemin_abs.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Fichier trop volumineux",
                )
            sortie.write(chunk)

    return (
        str(dossier_rel / nom_stocke),
        taille,
        mime_depuis_extension(extension),
    )
