// The Cape Pool Journal — small progressive enhancements (site works without JS)
(function () {
  // Mobile menu
  var btn = document.querySelector('.menu-btn'), nav = document.querySelector('nav.main');
  if (btn && nav) btn.addEventListener('click', function () {
    var open = nav.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  // Reading progress + active TOC link (post pages)
  var bar = document.querySelector('.progress'), article = document.querySelector('.post-main');
  var tocLinks = [].slice.call(document.querySelectorAll('aside .toc a'));
  var heads = tocLinks.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
  function onScroll() {
    if (bar && article) {
      var r = article.getBoundingClientRect(), h = r.height - window.innerHeight;
      bar.style.width = Math.max(0, Math.min(100, (-r.top / (h > 0 ? h : 1)) * 100)) + '%';
    }
    var current = -1;
    heads.forEach(function (el, i) { if (el && el.getBoundingClientRect().top < 120) current = i; });
    tocLinks.forEach(function (a, i) { a.classList.toggle('active', i === current); });
  }
  if (bar || tocLinks.length) { window.addEventListener('scroll', onScroll, { passive: true }); onScroll(); }

  // Search filter (home page)
  var q = document.getElementById('q');
  if (q) {
    var cards = [].slice.call(document.querySelectorAll('[data-search]')), empty = document.querySelector('.empty');
    q.addEventListener('input', function () {
      var t = q.value.trim().toLowerCase(), shown = 0;
      cards.forEach(function (c) {
        var hit = !t || c.getAttribute('data-search').indexOf(t) > -1;
        c.style.display = hit ? '' : 'none'; if (hit) shown++;
      });
      if (empty) empty.style.display = shown ? 'none' : 'block';
      if (t && document.getElementById('latest')) document.getElementById('latest').scrollIntoView({ block: 'start' });
    });
    var form = q.closest('form'); if (form) form.addEventListener('submit', function (e) { e.preventDefault(); });
  }

  // Copy link
  var copy = document.querySelector('[data-copy]');
  if (copy) copy.addEventListener('click', function () {
    var done = function () { copy.textContent = 'Link copied'; setTimeout(function () { copy.textContent = 'Copy link'; }, 2000); };
    if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(done, done); else done();
  });

  // Cookie notice (only rendered when ads/analytics are on)
  var c = document.querySelector('.cookie');
  if (c) {
    var seen = false;
    try { seen = localStorage.getItem('cpj-cookie-ok') === '1'; } catch (e) {}
    if (!seen) c.classList.add('show');
    var ok = c.querySelector('button');
    if (ok) ok.addEventListener('click', function () {
      try { localStorage.setItem('cpj-cookie-ok', '1'); } catch (e) {}
      c.classList.remove('show');
    });
  }

  // AdSense: fill each ad unit once the library is present
  if (document.querySelector('ins.adsbygoogle')) {
    [].forEach.call(document.querySelectorAll('ins.adsbygoogle'), function () {
      try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) {}
    });
  }
})();
