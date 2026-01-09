name: ✨ Feature Request
description: Proposer une nouvelle fonctionnalité
title: "[FEATURE] "
labels: ["enhancement"]

body:
  - type: textarea
    attributes:
      label: Description
      description: Description claire de la fonctionnalité demandée
      placeholder: "Je souhaiterais..."
    validations:
      required: true

  - type: textarea
    attributes:
      label: Cas d'usage
      description: Pourquoi cette fonctionnalité serait-elle utile?
    validations:
      required: true

  - type: textarea
    attributes:
      label: Solution proposée
      description: Description de la solution
    validations:
      required: true

  - type: textarea
    attributes:
      label: Alternatives envisagées
      description: Description des alternatives
