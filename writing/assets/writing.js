// Writing pages: mood switch (shared with the home page), language switch, the pet, reading progress.
(function () {
  var root = document.documentElement;
  var modes = ['night', 'light', 'train'];
  var topColor = { night: '#3A1F18', light: '#A9B9CC', train: '#0A0E0E' };
  var meta = document.querySelector('meta[name="theme-color"]');
  var all = function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); };

  // ---------- mood ----------
  var modeButtons = all('.switch button');
  function setMode(mode, remember) {
    if (modes.indexOf(mode) < 0) mode = 'night';
    root.setAttribute('data-mode', mode);
    modeButtons.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-set') === mode)); });
    if (meta) meta.setAttribute('content', topColor[mode]);
    if (remember) { try { localStorage.setItem('vq-mode', mode); } catch (e) {} }
  }
  setMode(root.getAttribute('data-mode') || 'night', false);
  modeButtons.forEach(function (b) {
    b.addEventListener('click', function () { setMode(b.getAttribute('data-set'), true); });
  });

  // ---------- language ----------
  var langButtons = all('[data-lang-set]');
  var titles = { zh: root.getAttribute('data-title-zh'), en: root.getAttribute('data-title-en') };
  function setLang(lang, remember) {
    if (lang !== 'zh' && lang !== 'en') lang = 'en';
    root.setAttribute('data-lang', lang);
    root.setAttribute('lang', lang === 'zh' ? 'zh-Hans' : 'en');
    langButtons.forEach(function (b) {
      if (b.hasAttribute('aria-pressed')) b.setAttribute('aria-pressed', String(b.getAttribute('data-lang-set') === lang));
    });
    if (titles[lang]) document.title = titles[lang];
    if (remember) {
      try { localStorage.setItem('vq-lang', lang); } catch (e) {}
      try {
        var url = new URL(location.href);
        url.searchParams.set('lang', lang);
        history.replaceState(null, '', url.pathname + url.search + url.hash);
      } catch (e) {}
    }
  }
  setLang(root.getAttribute('data-lang'), false);
  langButtons.forEach(function (b) {
    b.addEventListener('click', function () {
      setLang(b.getAttribute('data-lang-set'), true);
      if (b.hasAttribute('data-to-top')) window.scrollTo(0, 0);
    });
  });

  // ---------- boop the pet ----------
  all('.pet').forEach(function (p) {
    function boop() {
      p.classList.remove('pop');
      void p.getBoundingClientRect();
      p.classList.add('pop');
    }
    p.addEventListener('click', boop);
    p.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); boop(); } });
    p.addEventListener('animationend', function (e) { if (e.animationName === 'heart') p.classList.remove('pop'); });
  });

  // ---------- reading progress ----------
  var bar = document.querySelector('.progress');
  if (bar) {
    var ticking = false;
    var update = function () {
      ticking = false;
      var max = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = (max > 0 ? Math.min(100, Math.max(0, (window.scrollY / max) * 100)) : 0) + '%';
    };
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
    window.addEventListener('resize', update);
    update();
  }
})();
