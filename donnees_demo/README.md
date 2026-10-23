# Données de démonstration

Ce dossier regroupe tout ce qui sert à peupler une instance avec un jeu
d'exemple : captures d'écran du dépôt, découverte de l'application, et
contribution sans avoir à saisir des dizaines de candidatures à la main.

> **Toutes les données de ce dossier sont fictives.** Entreprises, contacts,
> adresses, liens et annonces sont inventés. Aucune donnée réelle ni
> personnelle ne doit être ajoutée ici : ce dossier, contrairement à `data/`,
> fait partie du dépôt public.

## Contenu

| Fichier | Rôle |
|---|---|
| `seed_demo.py` | Crée un compte de démonstration et six candidatures à différents stades, dont une complète (relances, contacts, entretien, annonce) pour illustrer la fiche détail et la frise chronologique. |
| `document_test.pdf` | PDF d'une page, valide et sans contenu réel, pour exercer le téléversement de documents (CV, lettre de motivation). |

## Tester le téléversement

Depuis la fiche d'une candidature, section Documents, téléversez
`document_test.pdf`. Son extension `.pdf` fait partie de la liste blanche par
défaut (`UPLOAD_EXTENSIONS`). Le fichier est ensuite servi en téléchargement
forcé, jamais rendu par le navigateur : c'est le comportement attendu, décrit
dans [SECURITE.md](../SECURITE.md).

Pour vérifier le refus d'une extension non autorisée, renommez une copie en
`.html` : le téléversement doit échouer avec un message explicite.

## Lancer le jeu de démonstration

Depuis la racine du projet, l'application étant démarrée :

```bash
docker compose exec app python donnees_demo/seed_demo.py
```

Identifiants créés :

```
demo@exemple.fr / demo
```

En local, hors Docker, en dirigeant les données vers un dossier jetable :

```bash
DATA_DIR=/tmp/demo python donnees_demo/seed_demo.py
```

## À savoir

- **À lancer sur une base vierge.** Le script s'arrête sans rien modifier si le
  compte `demo@exemple.fr` existe déjà. Il n'efface jamais de données
  existantes, mais il n'a pas vocation à cohabiter avec un usage réel.
- **Ne le lancez pas sur votre base de production.** Pour repartir d'une base
  vierge dédiée aux captures, arrêtez le conteneur, videz `data/`, puis
  redémarrez.
- **Le mot de passe `demo` est volontairement trivial.** Il n'est destiné qu'à
  une instance de démonstration locale, jamais à une instance exposée.
- Le script ajoute la racine du projet à `sys.path`, ce qui lui permet d'être
  lancé directement depuis ce sous-dossier tout en important les modules
  `app.*`.

## Captures d'écran

Les captures du README principal doivent être régénérées depuis une instance
alimentée par ce script, en navigation privée, et déposées dans
`docs/captures/`. Les anciennes captures ont été supprimées car elles
contenaient de vraies données personnelles.
