/*
  Comportements d'interface qui etaient portes par des attributs
  onclick / onsubmit dans les gabarits.

  Externalises ici pour permettre une Content-Security-Policy sans
  'unsafe-inline' sur script-src : les gestionnaires d'evenements inline
  sont bloques par une CSP stricte, au meme titre qu'un <script> inline.

  Deux comportements, par delegation sur le document (donc valables pour
  tout element ajoute plus tard) :

  - [data-href]      : l'element entier devient cliquable et navigue vers
                       l'URL indiquee (lignes du tableau d'accueil).
  - [data-confirmer] : la soumission du formulaire demande confirmation,
                       et est annulee si l'utilisateur refuse.
*/

(function () {
  document.addEventListener("click", function (e) {
    const cible = e.target.closest("[data-href]");
    if (!cible) return;
    // Un lien, un bouton ou un champ a l'interieur garde son propre
    // comportement : on ne detourne pas le clic.
    if (e.target.closest("a, button, input, select, textarea, label")) return;
    window.location.href = cible.getAttribute("data-href");
  });

  document.addEventListener("submit", function (e) {
    const formulaire = e.target.closest("[data-confirmer]");
    if (!formulaire) return;
    if (!window.confirm(formulaire.getAttribute("data-confirmer"))) {
      e.preventDefault();
    }
  });
})();
