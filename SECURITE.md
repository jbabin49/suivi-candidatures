# Démarche de sécurité

Ce document décrit la démarche de sécurité appliquée au projet : comment il a
été audité, ce qui a été corrigé, ce qui a été vérifié, et ce qui reste à la
charge de la personne qui déploie l'application.

Audit initial, correctifs et vérification de clôture : 23 octobre 2026.

## Méthode, et ses limites

**À lire avant toute autre section.** La portée de ce document dépend
entièrement de la manière dont il a été produit.

- L'audit, la revue de code et les correctifs ont été réalisés **avec
  l'assistance de Claude Code (IA)**, en dialogue avec l'auteur du projet.
- **Ce n'est pas un audit de sécurité humain indépendant.** Aucun tiers n'a
  relu ces conclusions.
- **Ce n'est pas un test d'intrusion professionnel.** Aucune campagne
  d'exploitation n'a été menée contre une instance déployée : pas de fuzzing,
  pas de scan réseau, pas de test de résistance à la force brute.
- Une partie des conclusions provient d'une **revue manuelle assistée** du
  code, et non des scanners. Les outils automatiques n'ont remonté que 4 des
  22 constats initiaux ; les plus sérieux ont été trouvés en lisant le code.
- Cette revue manuelle assistée peut comporter des erreurs. Exemple concret
  survenu pendant ce travail : l'inventaire initial affirmait qu'un bloc
  `<script type="application/json">` échappait au champ de la politique de
  sécurité du contenu. C'est vrai sur Chrome, faux sur Firefox. L'erreur a été
  détectée par le test en navigateur de l'auteur, pas par l'analyse.
- **Le test fonctionnel de l'interface a été réalisé manuellement dans le
  navigateur par l'auteur du projet**, en navigation privée. C'est ce test, et
  non les outils, qui a validé que la politique de sécurité du contenu ne casse
  aucune fonctionnalité.
- La suite automatisée compte 31 tests. Elle valide des propriétés de sécurité
  précises (isolation entre utilisateurs, refus d'extensions de fichiers,
  en-têtes HTTP, drapeaux du cookie, schémas d'URL), mais elle ne couvre **pas**
  le flux OIDC, faute de fournisseur d'identité de test.

### Outils utilisés

| Outil | Version | Périmètre |
|---|---|---|
| `bandit` | 1.9.4 | `bandit -r app/` |
| `pip-audit` | 2.10.1 | `pip-audit -r requirements.txt` |
| `semgrep` | 1.182.1 | packs `p/python`, `p/security-audit`, `p/jwt`, `p/sql-injection`, `p/xss` sur `app/` |
| `semgrep` | 1.182.1 | packs `p/dockerfile`, `p/secrets` sur la racine |
| `pytest` | 31 tests | exécutés dans un conteneur Python 3.12 |
| `trivy` | 0.76.1 | `trivy fs .` (vulnérabilités des dépendances et secrets) et `trivy config .` (`Dockerfile` et `docker-compose.yml`) |

`semgrep --config auto` n'a pas été utilisé : il exige l'activation de la
télémétrie vers semgrep.dev. Les packs ci-dessus ont été retenus à la place.

**`trivy` a été exécuté.** `trivy fs .` ne remonte aucune vulnérabilité ni
aucun secret. `trivy config .` a remonté une seule mauvaise configuration, de
gravité faible : DS-0026, l'absence d'instruction `HEALTHCHECK` dans le
`Dockerfile`. Elle est désormais corrigée.

## Findings corrigés

Niveau de détail volontairement limité à « quel type de faille, comment elle
est corrigée ». Les modes opératoires d'exploitation ne sont pas publiés.

| # | Gravité | Type de faille | Fichier concerné | Correctif appliqué | Statut |
|---|---|---|---|---|---|
| 1 | Critique | Dépendance vulnérable : contournement d'authentification possible en mode OIDC (forge de jeton, validation incomplète des jetons d'identité). 10 CVE, dont CVE-2026-27962 et CVE-2026-28498 | `requirements.txt` | `authlib` 1.3.2 vers 1.9.1. Compatibilité de l'API vérifiée par introspection | Corrigé le 23/10/2026 |
| 2 | Élevé | Cross-site scripting stockée via document téléversé : aucun contrôle d'extension, et type MIME fourni par le client réutilisé pour servir le fichier | `app/routes/documents.py`, `app/routes/profil.py` | Liste blanche d'extensions contrôlée avant écriture, type MIME redéterminé côté serveur, et téléchargement forcé avec type opaque et `nosniff` à la consultation. Logique factorisée dans `app/services/fichiers.py` | Corrigé le 23/10/2026 |
| 3 | Élevé | Conteneur exécuté avec les privilèges `root` | `Dockerfile` | Utilisateur non privilégié (UID 1000) et directive `USER`. Le code reste propriété de `root`, non modifiable par le processus | Corrigé le 23/10/2026 |
| 4 | Élevé | Dépendance vulnérable : déni de service par épuisement CPU, atteignable sans authentification. 7 CVE, dont CVE-2026-53539 | `requirements.txt` | `python-multipart` 0.0.17 vers 0.0.32 | Corrigé le 23/10/2026 |
| 5 | Élevé | Divulgation d'information : pages de documentation générées par FastAPI (`/docs`, `/redoc`, `/openapi.json`) accessibles sans authentification. L'application n'expose pas d'API, mais ces pages décrivent toutes ses routes et tous ses champs de formulaire | `app/main.py` | Nouvelle option `ENABLE_DOCS`, à `false` par défaut. Les routes sont retirées, pas seulement protégées | Corrigé le 23/10/2026 |
| 7 | Moyen | Injection JSON dans HTML : données de la frise sérialisées sans échappement, via le filtre `\| safe` | `app/templates/candidature.html`, `app/routes/candidatures.py` | Transmission par attribut `data-*` sérialisé avec le filtre `tojson`. Il ne reste aucun `\| safe` dans le projet | Corrigé le 23/10/2026 |
| 9 | Moyen | Dépendance vulnérable : plusieurs dénis de service et injections d'en-tête. 7 CVE, dont CVE-2025-62727 et CVE-2026-48710 | `requirements.txt` | `fastapi` 0.115.5 vers 0.161.1, tirant `starlette` 1.9.0. Compatibilité vérifiée par analyse AST des 38 appels concernés | Corrigé le 23/10/2026 |
| 11 | Moyen | Cookie de session sans paramètre explicite : pas de drapeau `Secure` configurable, durée de vie de 14 jours | `app/main.py` | `SESSION_COOKIE_SECURE` et `SESSION_MAX_AGE` (défaut 12 heures), et `SameSite=Lax` posé explicitement | Corrigé le 23/10/2026 |
| 14 | Élevé (réévalué) | Absence d'en-têtes de sécurité : aucune politique de sécurité du contenu, aucune protection contre le reniflage de type ni contre l'inclusion en iframe | `app/main.py` | Middleware global posant une politique stricte, `X-Content-Type-Options` et `Referrer-Policy`. Les trois éléments de script inline ont été externalisés pour permettre `script-src 'self'` sans `'unsafe-inline'` | Corrigé le 23/10/2026 |
| 15 | Faible | Injection de schéma d'URL : le lien d'un contact était rendu dans un attribut `href` sans contrôle de schéma | `app/routes/contacts.py`, `app/templates/candidature.html` | Validation serveur par liste blanche (`http` et `https` uniquement), plus un garde-fou à l'affichage pour les données antérieures. Complément automatique en `https://` pour un domaine nu | Corrigé le 23/10/2026 |
| 19 | Faible | Dépendance vulnérable : évasions de bac à sable de gabarits. 3 CVE | `requirements.txt` | `jinja2` 3.1.4 vers 3.1.6. Non exploitable ici, aucun gabarit n'étant fourni par un utilisateur | Corrigé le 23/10/2026 |
| 24 | Hors sécurité applicative | Données personnelles réelles dans les captures d'écran du dépôt | `docs/captures/` | Captures supprimées, références du README neutralisées. À régénérer depuis un jeu de données fictives | Corrigé le 23/10/2026 |
| 25 | Faible | Absence de `HEALTHCHECK` conteneur : aucune sonde de santé déclarée dans l'image, l'orchestrateur ne pouvait pas distinguer un conteneur démarré d'un conteneur en état de fonctionner (`trivy` DS-0026) | `Dockerfile` | Ajout d'une instruction `HEALTHCHECK` interrogeant `/healthz`, la route déjà utilisée par `docker-compose.yml` | Corrigé le 24/10/2026 |

La numérotation suit l'inventaire complet des 24 constats de l'audit, d'où les
numéros manquants dans ce tableau : ils correspondent aux risques résiduels
assumés, listés dans leur propre section plus bas, et aux signalements d'outils
écartés comme faux positifs, documentés en fin de document. Le constat 25 est
postérieur à cet audit : il vient du passage de `trivy`.

### Politique de sécurité du contenu retenue

```
default-src 'self'; script-src 'self'; style-src 'self';
style-src-attr 'unsafe-inline'; img-src 'self'; font-src 'self';
object-src 'none'; base-uri 'none'; form-action 'self';
frame-ancestors 'none'
```

L'application ne charge aucune ressource distante : pas de CDN, pas de police
externe, pas d'appel réseau depuis le JavaScript. `script-src` reste donc en
`'self'` strict. Seule concession, `style-src-attr 'unsafe-inline'`, pour les
attributs `style="..."` cosmétiques des gabarits ; les blocs `<style>` et les
feuilles distantes restent interdits.

La politique a d'abord été déployée en mode `Report-Only`, le temps de valider
chaque page dans la console du navigateur, puis basculée en mode bloquant. Le
nom de l'en-tête est une constante unique dans `app/main.py`, ce qui permet de
repasser en `Report-Only` en cas de régression.

## Points vérifiés et jugés sains

Ces points ont été vérifiés par lecture du code, et non supposés corrects.

**Injection SQL : aucune.** Tous les accès passent par l'ORM SQLAlchemy. Aucune
concaténation ni interpolation de requête dans le projet. Le seul SQL littéral
concerne deux `PRAGMA` SQLite, sans aucun paramètre externe.

**Isolation entre utilisateurs : correcte.** Les 19 routes fonctionnelles
dépendent toutes de la résolution de l'utilisateur courant, vérifié par analyse
AST des signatures et non par recherche textuelle. Chaque accès à une ressource
contrôle son appartenance. Les entités rattachées à une candidature sont
filtrées après contrôle de propriété du parent. Une ressource appartenant à
autrui renvoie 404 et non 403, pour ne pas révéler son existence. Un test
automatisé couvre cette isolation.

**Traversée de chemin au téléversement : non exploitable.** Le nom de stockage
est un identifiant aléatoire suivi de l'extension validée, et les segments de
dossier sont des entiers. Aucun nom de fichier fourni par le client ne permet
de sortir du dossier cible.

**En-tête `Content-Disposition` : pas d'injection.** Le nom de fichier d'origine
est encodé par Starlette, qui bascule sur la forme `filename*=utf-8''` dès
qu'un caractère doit l'être.

**Hachage des mots de passe : correct.** `argon2-cffi` avec les paramètres par
défaut de `PasswordHasher`, sel automatique par mot de passe, aucun mot de passe
stocké ni journalisé en clair. Les comptes OIDC ne peuvent pas se connecter par
le formulaire local.

**Flux OIDC : validations déléguées à la bibliothèque.** `state`, `nonce`,
`issuer`, `aud` et `exp` sont validés par authlib. L'état est stocké en session
et non en cache. La solidité de ce flux dépend donc de la version d'authlib,
d'où la priorité donnée au finding 1. **Ce flux n'est couvert par aucun test
automatisé** et n'a pas été exercé de bout en bout pendant cet audit.

**Échappement des gabarits : automatique et sans exception.** L'échappement
Jinja2 est actif par défaut, et **il ne reste aucun `| safe` dans le projet**,
ce qu'un test vérifie.

**Secrets en dur : aucun.** La clé de session est générée aléatoirement au
premier démarrage et persistée en 0600 dans le volume de données, lui-même
exclu du dépôt et de l'image.

**Politique de sécurité du contenu : effective, pas seulement déclarée.**
Vérifiée sur chaque page rendue par le conteneur : aucun élément `<script>`
sans attribut `src`, sur aucune page.

## Risques résiduels assumés

Ces points sont connus, jugés proportionnés à un usage auto-hébergé, et non
corrigés. Chacun indique comment le durcir.

**Pas de jeton anti-CSRF.** La protection repose sur l'attribut `SameSite=Lax`
du cookie de session, désormais posé explicitement, qui empêche le navigateur
d'envoyer le cookie sur une requête `POST` provenant d'un autre site. C'est une
protection unique, sans défense en profondeur, ce qui serait insuffisant pour
une application exposée à un large public. *Durcir* : ajouter un jeton par
formulaire, vérifié dans une dépendance commune aux routes `POST`.

**Session non révocable, durée de 12 heures.** La session est un cookie signé,
sans état côté serveur : aucune session précise ne peut être révoquée à
distance. Seule la suppression de la clé de session, suivie d'un redémarrage,
invalide toutes les sessions. La durée a été ramenée de 14 jours à 12 heures
pour limiter la fenêtre d'usage d'un cookie dérobé. *Durcir* : réduire
`SESSION_MAX_AGE`, ou passer à des sessions persistées en base.

**Cookie sans drapeau `Secure` par défaut.** `SESSION_COOKIE_SECURE=false` est
le défaut, car un cookie `Secure` est ignoré par le navigateur sur une origine
`http://`, ce qui empêcherait toute connexion en HTTP local. *Durcir* :
**passer cette variable à `true` dès que l'application est servie en HTTPS.**
Sans cela, le cookie de session circule en clair.

**Pas de HTTPS en propre.** L'application sert du HTTP en clair ; le chiffrement
du transport est entièrement délégué à un reverse proxy, non fourni par ce
projet. *Durcir* : placer l'application derrière un reverse proxy avec un
certificat valide.

**Port publié sur toutes les interfaces.** `docker-compose.yml` publie
`8000:8000`, ce qui expose l'application à tout le réseau local. C'est le
comportement attendu pour un démarrage immédiat sans reverse proxy. *Durcir* :
passer à `127.0.0.1:8000:8000`, ou retirer la publication de port et laisser le
reverse proxy communiquer par le réseau Docker.

**Mot de passe du compte initial en clair dans l'environnement.**
`ADMIN_PASSWORD` reste lisible dans l'environnement du conteneur après le
premier démarrage. Le fichier `.env` est exclu du dépôt et de l'image.
*Durcir* : vider `ADMIN_EMAIL` et `ADMIN_PASSWORD` après création du premier
compte, puis utiliser `creer_utilisateur.py`.

**Énumération de comptes par canal temporel.** Pour une adresse inconnue, la
vérification retourne avant tout calcul de hachage, donc plus vite que pour une
adresse connue. Sur une instance personnelle, l'information obtenue est
négligeable, et le message d'erreur reste indifférencié. *Durcir* : calculer
systématiquement un hachage, y compris face à une adresse inconnue.

**Pas de limitation de débit à la connexion.** Aucun verrouillage ni
journalisation des échecs d'authentification. Argon2 ralentit une attaque par
force brute mais ne l'empêche pas. C'est le point le plus important restant à
traiter, et il devient réel dès que l'instance est joignable depuis Internet.
*Durcir* : limiter les tentatives par adresse IP et par compte, et journaliser
les échecs.

**Plafond de téléversement appliqué tardivement.** Le corps de la requête est
écrit sur disque par le serveur avant que l'application ne puisse vérifier sa
taille. *Durcir* : plafonner la taille du corps au niveau du reverse proxy.

**Provisionnement OIDC sans filtre.** En mode OIDC, tout compte existant chez le
fournisseur d'identité obtient un compte applicatif au premier login, et la
vérification de l'adresse n'est pas contrôlée. *Durcir* : ajouter une liste
d'autorisation (groupe, domaine d'adresse, ou liste explicite de sujets) et
contrôler la revendication `email_verified`.

**Reconstruction d'URL derrière un reverse proxy.** uvicorn n'est pas lancé avec
`--proxy-headers`, et aucune validation de l'en-tête `Host` n'est en place.
*Durcir* : ajouter `--proxy-headers --forwarded-allow-ips` et un
`TrustedHostMiddleware`.

**Chaîne d'approvisionnement non verrouillée.** L'image de base est référencée
par un tag mobile, et les dépendances ne sont pas épinglées par empreinte.
*Durcir* : épingler l'image par empreinte et générer un `requirements.txt` avec
hachages.

**Export CSV et formules de tableur.** Un champ commençant par `=`, `+`, `-` ou
`@` peut être interprété comme une formule à l'ouverture dans un tableur. Les
données étant saisies par l'utilisateur lui-même, le risque le concerne
d'abord. *Durcir* : préfixer ces champs d'une apostrophe à l'export.

## Résultat de la vérification de clôture

Outils relancés le 23 octobre 2026, après tous les correctifs. `trivy` a été
exécuté le 24 octobre 2026 : ses deux passes sont postérieures aux correctifs,
sans mesure antérieure à laquelle les comparer.

| Outil | Avant | Après |
|---|---|---|
| `pip-audit` | 51 vulnérabilités sur 4 paquets | **0** |
| `bandit -r app/` | 1 signalement (faux positif) | 1 signalement (même faux positif) |
| `semgrep` packs applicatifs | 3 signalements | **1** (faux positif documenté) |
| `semgrep` packs `dockerfile` et `secrets` | 1 signalement | **0** |
| `pytest` | 8 tests | **31 tests, tous verts** |
| `trivy fs .` | premier passage après correctifs | **0 vulnérabilité, 0 secret** |
| `trivy config .` | 1 mauvaise configuration (DS-0026, gravité faible) | **0** |

### Faux positifs conservés

**`bandit` B105, « hardcoded password »** sur la comparaison de la clé de
session à sa valeur sentinelle par défaut. Ce n'est pas un secret, mais la
valeur témoin qui déclenche la génération d'une clé aléatoire. Conservé sans
annotation `# nosec` : masquer le signalement supprimerait un contrôle utile sur
les futures modifications.

**`semgrep` `var-in-href`** sur le lien d'un contact. La règle signale toute
variable de gabarit dans un `href`, sans pouvoir déterminer si elle est validée.
Ici la valeur est filtrée deux fois, à l'enregistrement et à l'affichage. Le
signalement subsiste parce que la règle est purement syntaxique.

## Avertissement

**Ce document n'est pas un gage de sécurité.** Il décrit un état des lieux à une
date, obtenu par une méthode dont les limites sont exposées en tête de document.
L'absence de finding sur un point ne prouve pas l'absence de défaut : elle
indique seulement que rien n'a été trouvé avec les moyens employés.

**La personne qui déploie cette application reste responsable de son
installation.** En particulier :

- **HTTPS** : l'application ne chiffre rien elle-même. Servez-la derrière un
  reverse proxy avec un certificat valide, et passez alors
  `SESSION_COOKIE_SECURE=true`.
- **Exposition réseau** : ne publiez le port que vers ce qui en a besoin. Sur
  Internet, un reverse proxy est le minimum, et une authentification en amont
  est préférable.
- **Sauvegardes** : tout vit dans `data/`, base de données, documents téléversés
  et clé de session. Sauvegardez ce dossier et testez une restauration.
- **Mises à jour** : relancez `pip-audit -r requirements.txt` régulièrement. Les
  versions épinglées ici sont saines au 23 octobre 2026, pas indéfiniment.
- **Données personnelles** : cette application stocke des CV, des lettres de
  motivation et des coordonnées. Traitez le volume `data/` comme des données
  personnelles, et ne publiez jamais de capture d'écran issue d'une instance
  réelle.

## Signaler une vulnérabilité

Si vous constatez un problème de sécurité, ouvrez une issue décrivant le
problème sans y publier d'élément permettant de l'exploiter directement, ou
contactez l'auteur en privé.
