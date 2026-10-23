"""
Tests des en-tetes de securite poses par le middleware global.

La CSP est pour l'instant emise en Report-Only : le test suit ce choix et
devra etre ajuste lors du passage en mode bloquant.
"""

from __future__ import annotations

from app.main import CSP, EN_TETE_CSP


def test_entetes_de_securite_sur_une_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers[EN_TETE_CSP] == CSP
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"


def test_csp_sans_unsafe_inline_sur_les_scripts():
    """Le durcissement ne vaut que si script-src reste strict."""
    assert "script-src 'self'" in CSP
    assert "script-src 'self' 'unsafe-inline'" not in CSP
    # La seule concession autorisee porte sur les attributs de style.
    assert CSP.count("'unsafe-inline'") == 1
    assert "style-src-attr 'unsafe-inline'" in CSP


def test_entetes_presents_aussi_sur_une_redirection(client):
    """Une reponse 303 ou 401 doit elle aussi porter les en-tetes."""
    r = client.post("/logout")
    assert r.status_code == 303
    assert r.headers["x-content-type-options"] == "nosniff"
    assert EN_TETE_CSP in r.headers
