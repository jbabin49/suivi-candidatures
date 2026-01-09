name: 🐛 Bug Report
description: Signaler un bug
title: "[BUG] "
labels: ["bug"]

body:
  - type: textarea
    attributes:
      label: Description
      description: Description claire et concise du bug
      placeholder: "Le problème est..."
    validations:
      required: true

  - type: textarea
    attributes:
      label: Étapes pour reproduire
      description: Étapes précises pour reproduire le bug
      placeholder: |
        1. Aller à '...'
        2. Cliquer sur '...'
        3. Voir l'erreur '...'
    validations:
      required: true

  - type: textarea
    attributes:
      label: Comportement attendu
      description: Description de ce qui devrait se passer
    validations:
      required: true

  - type: textarea
    attributes:
      label: Comportement actuel
      description: Description de ce qui se passe réellement

  - type: input
    attributes:
      label: Version Node.js
      placeholder: "18.x.x"
    validations:
      required: true

  - type: input
    attributes:
      label: Système d'exploitation
      placeholder: "Windows 10, macOS 12, Ubuntu 22.04"
    validations:
      required: true

  - type: textarea
    attributes:
      label: Screenshots/Logs
      description: Ajoutez des screenshots ou logs si applicable
