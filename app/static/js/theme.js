/*
  Bascule du theme clair/sombre.

  Par defaut l'application suit le theme du systeme (via la media query
  CSS prefers-color-scheme). Ce script permet de forcer un mode et de
  memoriser ce choix dans le navigateur (localStorage), en posant
  l'attribut data-theme sur <html>.

  L'initialisation est faite tres tot (dans le <head>) pour eviter tout
  clignotement ; ce fichier gere ensuite le bouton de bascule.
*/

(function () {
  const cle = "theme";

  function themeSysteme() {
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function themeActuel() {
    return document.documentElement.getAttribute("data-theme") || themeSysteme();
  }

  function appliquer(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try {
      localStorage.setItem(cle, theme);
    } catch (e) {
      /* stockage indisponible : on ignore, le choix ne sera pas memorise */
    }
    majBouton(theme);
  }

  function majBouton(theme) {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.textContent = theme === "dark" ? "Mode clair" : "Mode sombre";
  }

  document.addEventListener("DOMContentLoaded", function () {
    majBouton(themeActuel());
    const btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.addEventListener("click", function () {
        appliquer(themeActuel() === "dark" ? "light" : "dark");
      });
    }
  });
})();
