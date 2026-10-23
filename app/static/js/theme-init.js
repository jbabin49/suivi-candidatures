/*
  Application du theme memorise, avant le rendu de la page.

  Ce fichier est charge tres tot dans le <head>, sans defer, donc de
  maniere synchrone : le theme est pose sur <html> avant le premier
  affichage, ce qui evite le clignotement clair/sombre. La bascule du
  bouton est geree ensuite par theme.js.

  Externalise depuis un <script> inline de base.html pour permettre une
  Content-Security-Policy sans 'unsafe-inline' sur script-src.
*/

(function () {
  try {
    var t = localStorage.getItem("theme");
    if (t) document.documentElement.setAttribute("data-theme", t);
  } catch (e) {}
})();
