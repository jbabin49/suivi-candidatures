/*
  Rendu SVG de la frise chronologique d'une candidature.

  Lit les evenements injectes dans la page par l'attribut data-evenements
  du conteneur #frise, puis dessine un axe horizontal avec un point par
  evenement, positionne
  proportionnellement a sa date. Les etiquettes (libelle + date) alternent
  au-dessus et en dessous de l'axe pour ne pas se chevaucher. La couleur
  du texte depend du type d'evenement.

  La hauteur est volontairement compacte. Pas de dependance externe :
  SVG genere a la main, imprimable tel quel.
*/

(function () {
  const cible = document.getElementById("frise");
  if (!cible || cible.dataset.evenements === undefined) return;

  let evenements;
  try {
    evenements = JSON.parse(cible.dataset.evenements);
  } catch (e) {
    return;
  }
  if (!evenements.length) {
    cible.textContent = "Aucun événement à afficher pour le moment.";
    cible.style.color = "var(--texte-doux)";
    cible.style.fontSize = "0.9rem";
    cible.style.padding = "0.4rem 0";
    return;
  }

  // Couleur de l'etiquette selon le type (variables CSS pour suivre le theme).
  const couleur = (ev) => {
    if (ev.type === "candidature") return "var(--c-neutre)";
    if (ev.type === "relance") return "var(--c-relance)";
    if (ev.type === "entretien") return "var(--c-entretien)";
    if (ev.type === "reponse")
      return ev.issue === "offre" ? "var(--c-favorable)" : "var(--c-refus)";
    return "var(--texte)";
  };

  // Dimensions compactes.
  const largeur = 680;
  const hauteur = 130;
  const margeG = 40;
  const margeD = 40;
  const axeY = 65;
  const zone = largeur - margeG - margeD;

  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("width", "100%");
  svg.setAttribute("viewBox", `0 0 ${largeur} ${hauteur}`);
  svg.setAttribute("role", "img");
  svg.style.minWidth = "520px"; // garde la lisibilite, le conteneur scrolle si besoin

  const axeCouleur = "var(--texte)";
  const traitDoux = "var(--bordure-forte)";

  const ligne = (x1, y1, x2, y2, couleurTrait, epaisseur) => {
    const l = document.createElementNS(svgNS, "line");
    l.setAttribute("x1", x1); l.setAttribute("y1", y1);
    l.setAttribute("x2", x2); l.setAttribute("y2", y2);
    l.setAttribute("stroke", couleurTrait);
    l.setAttribute("stroke-width", epaisseur);
    svg.appendChild(l);
  };

  const texte = (x, y, contenu, couleurTexte, gras) => {
    const t = document.createElementNS(svgNS, "text");
    t.setAttribute("x", x); t.setAttribute("y", y);
    t.setAttribute("text-anchor", "middle");
    t.setAttribute("fill", couleurTexte);
    t.setAttribute("font-size", gras ? "13" : "11");
    t.setAttribute("font-family", "system-ui, sans-serif");
    if (gras) t.setAttribute("font-weight", "600");
    t.textContent = contenu;
    svg.appendChild(t);
  };

  // Axe principal et embouts.
  ligne(margeG, axeY, largeur - margeD, axeY, axeCouleur, 1);
  ligne(margeG, axeY - 7, margeG, axeY + 7, axeCouleur, 1);
  ligne(largeur - margeD, axeY - 7, largeur - margeD, axeY + 7, axeCouleur, 1);

  evenements.forEach((ev, i) => {
    const x = margeG + ev.position * zone;
    const dessus = i % 2 === 0; // alternance haut/bas
    const col = couleur(ev);

    // Tick sur l'axe.
    ligne(x, axeY - 7, x, axeY + 7, axeCouleur, 1);

    if (dessus) {
      ligne(x, axeY - 7, x, axeY - 20, traitDoux, 0.5);
      texte(x, axeY - 30, ev.libelle, col, true);
      texte(x, axeY - 17, ev.date, col, false);
    } else {
      ligne(x, axeY + 7, x, axeY + 20, traitDoux, 0.5);
      texte(x, axeY + 33, ev.libelle, col, true);
      texte(x, axeY + 47, ev.date, col, false);
    }
  });

  cible.appendChild(svg);
})();
