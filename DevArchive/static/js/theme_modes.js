(function () {
  var KEY = "sigaud-theme";
  var root = document.documentElement;

  function applyTheme(theme) {
    var safeTheme = theme === "dark" ? "dark" : "light";
    root.setAttribute("data-theme", safeTheme);
    try {
      localStorage.setItem(KEY, safeTheme);
    } catch (e) {}
    var btn = document.getElementById("theme-toggle-btn");
    if (btn) {
      btn.textContent = safeTheme === "dark" ? "Clair" : "Sombre";
      btn.setAttribute(
        "aria-label",
        safeTheme === "dark" ? "Activer le mode clair" : "Activer le mode sombre"
      );
    }
  }

  function initTheme() {
    var saved = "light";
    try {
      saved = localStorage.getItem(KEY) || "light";
    } catch (e) {}
    applyTheme(saved);
  }

  function findHost() {
    var selectors = [
      ".top-nav",
      ".main-header",
      ".header-inner",
      ".header",
      ".tools",
      "header",
      "nav"
    ];
    for (var i = 0; i < selectors.length; i++) {
      var el = document.querySelector(selectors[i]);
      if (el) return el;
    }
    return null;
  }

  function createToggle() {
    var wrap = document.createElement("div");
    wrap.className = "theme-toggle-wrap";
    var label = document.createElement("span");
    label.className = "theme-toggle-label";
    label.textContent = "Thème";
    var btn = document.createElement("button");
    btn.id = "theme-toggle-btn";
    btn.type = "button";
    btn.className = "theme-toggle-btn";
    btn.addEventListener("click", function () {
      var current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
      applyTheme(current === "dark" ? "light" : "dark");
    });
    wrap.appendChild(label);
    wrap.appendChild(btn);
    return wrap;
  }

  function attachToggle() {
    if (document.getElementById("theme-toggle-btn")) return;
    var host = findHost();
    var toggle = createToggle();
    if (host) {
      host.appendChild(toggle);
    } else {
      document.body.appendChild(toggle);
      toggle.style.position = "fixed";
      toggle.style.right = "16px";
      toggle.style.bottom = "16px";
      toggle.style.zIndex = "9999";
    }
    applyTheme(root.getAttribute("data-theme"));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initTheme();
      attachToggle();
    });
  } else {
    initTheme();
    attachToggle();
  }
})();
