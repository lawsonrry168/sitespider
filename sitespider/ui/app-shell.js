/** Shared shell: theme + brand mark */
(function () {
  const STORAGE_THEME = 'sitespider-theme';

  const BRAND_MARK_SRC = '/ui/brand-mark.svg';

  (function mountPolishCss() {
    if (document.querySelector('link[href="/ui/polish.css"]')) return;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/ui/polish.css';
    document.head.appendChild(link);
  })();

  (function mountSiteResetCss() {
    if (
      document.querySelector('link[href="/ui/site-reset.css"]') ||
      document.querySelector('link[href="/ui/site-v2.css"]')
    ) {
      return;
    }
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/ui/site-reset.css';
    document.head.appendChild(link);
  })();

  (function mountUxFriendlyCss() {
    if (document.querySelector('link[href="/ui/ux-friendly.css"]')) return;
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = '/ui/ux-friendly.css';
    document.head.appendChild(link);
  })();

  (function mountDesktopChrome() {
    if (!document.body || !document.body.classList.contains('app-console')) return;
    function addCss(href) {
      if (document.querySelector('link[href="' + href + '"]')) return;
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      document.head.appendChild(link);
    }
    addCss('/ui/desktop-gui.css');
    addCss('/ui/desktop-pages.css');
    if (document.querySelector('script[src="/ui/desktop-chrome.js"]')) return;
    var script = document.createElement('script');
    script.src = '/ui/desktop-chrome.js';
    script.defer = true;
    document.head.appendChild(script);
  })();

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
      btn.textContent = theme === 'light' ? '◐' : '◑';
      btn.title = theme === 'light' ? '切換深色' : '切換淺色';
    });
  }

  window.SiteSpiderShell = {
    initTheme: function () {
      var saved = 'dark';
      try { saved = localStorage.getItem(STORAGE_THEME) || 'dark'; } catch (_) {}
      applyTheme(saved);
      document.querySelectorAll('.theme-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var next = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
          try { localStorage.setItem(STORAGE_THEME, next); } catch (_) {}
          applyTheme(next);
        });
      });
    },
    mountBrand: function () {
      document.querySelectorAll('.brand-icon[data-brand]').forEach(function (el) {
        el.innerHTML =
          '<img class="brand-mark" src="' + BRAND_MARK_SRC + '" width="40" height="40" alt="" decoding="async">' +
          '<span class="logo-pulse"></span>';
      });
      document.querySelectorAll('.topbar .brand').forEach(function (el) {
        if (el.dataset.ssHomeLink) return;
        el.dataset.ssHomeLink = '1';
        el.setAttribute('role', 'link');
        el.setAttribute('tabindex', '0');
        el.setAttribute('title', '返回爬取中心');
        el.style.cursor = 'pointer';
        function go() { window.location.href = '/'; }
        el.addEventListener('click', function (e) {
          if (e.target.closest('button, a')) return;
          go();
        });
        el.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            go();
          }
        });
      });
    },
    setBrandActive: function (on) {
      document.querySelectorAll('.brand-icon[data-brand]').forEach(function (el) {
        el.classList.toggle('is-active', !!on);
      });
    },
    mountSkipLink: function () {
      if (!document.body.classList.contains('app-console')) return;
      if (document.getElementById('ss-skip-link')) return;
      var main =
        document.querySelector('.layout') ||
        document.querySelector('.page-wrap') ||
        document.querySelector('main');
      if (main && !main.id) main.id = 'main-content';
      var skip = document.createElement('a');
      skip.id = 'ss-skip-link';
      skip.className = 'skip-link';
      skip.href = '#main-content';
      skip.textContent = '跳至主要內容';
      document.body.insertBefore(skip, document.body.firstChild);
    },
    mountSiteFooter: function () {
      if (!document.body.classList.contains('app-console')) return;
      if (document.querySelector('.site-footer')) return;
      var year = new Date().getFullYear();
      var footer = document.createElement('footer');
      footer.className = 'site-footer';
      footer.setAttribute('role', 'contentinfo');
      footer.innerHTML =
        '<div class="site-footer-inner">' +
        '<div class="site-footer-brand">' +
        '<strong>SiteSpider</strong>' +
        '<span class="site-footer-tag">顧問級 SEO / GEO 交付</span>' +
        '</div>' +
        '<nav class="site-footer-nav" aria-label="網站資訊">' +
        '<a href="/guide">使用說明</a>' +
        '<a href="/about">關於我們</a>' +
        '<a href="/contact">聯絡我們</a>' +
        '<a href="/workspace">帳號與方案</a>' +
        '<a href="/pricing">方案價格</a>' +
        '<a href="/demo">範例報告</a>' +
        '</nav>' +
        '<p class="site-footer-copy">© ' + year + ' SiteSpider</p>' +
        '</div>';
      document.body.appendChild(footer);
    },
    toast: function (message, type) {
      type = type || 'info';
      var host = document.getElementById('ss-toast-host');
      if (!host) {
        host = document.createElement('div');
        host.id = 'ss-toast-host';
        host.className = 'ss-toast-host';
        host.setAttribute('aria-live', 'polite');
        host.setAttribute('aria-atomic', 'true');
        document.body.appendChild(host);
      }
      var el = document.createElement('div');
      el.className = 'ss-toast ss-toast--' + type;
      el.setAttribute('role', type === 'error' ? 'alert' : 'status');
      el.textContent = String(message || '');
      host.appendChild(el);
      requestAnimationFrame(function () { el.classList.add('is-visible'); });
      setTimeout(function () {
        el.classList.remove('is-visible');
        setTimeout(function () { el.remove(); }, 320);
      }, type === 'error' ? 5200 : 3600);
    },
    showBanner: function (targetId, message, type) {
      var box = typeof targetId === 'string' ? document.getElementById(targetId) : targetId;
      if (!box) return;
      box.className = 'ss-banner ss-banner--' + (type || 'info');
      box.textContent = String(message || '');
      box.classList.remove('hidden');
    },
    clearBanner: function (targetId) {
      var box = typeof targetId === 'string' ? document.getElementById(targetId) : targetId;
      if (!box) return;
      box.textContent = '';
      box.className = 'ss-banner hidden';
    },
    celebrate: function () {
      var existing = document.getElementById('ss-confetti');
      if (existing) existing.remove();
      var canvas = document.createElement('canvas');
      canvas.id = 'ss-confetti';
      canvas.className = 'confetti-canvas';
      canvas.setAttribute('aria-hidden', 'true');
      document.body.appendChild(canvas);
      var ctx = canvas.getContext('2d');
      var w = (canvas.width = window.innerWidth);
      var h = (canvas.height = window.innerHeight);
      var colors = ['#6ec9a0', '#8eddb6', '#8baee8', '#e8c468', '#f4f2ec'];
      var parts = [];
      for (var i = 0; i < 120; i++) {
        parts.push({
          x: Math.random() * w,
          y: Math.random() * h * -0.3 - 20,
          vx: (Math.random() - 0.5) * 4,
          vy: Math.random() * 3 + 2,
          rot: Math.random() * 360,
          vr: (Math.random() - 0.5) * 8,
          size: Math.random() * 6 + 3,
          color: colors[Math.floor(Math.random() * colors.length)],
        });
      }
      var start = performance.now();
      function frame(t) {
        var elapsed = t - start;
        ctx.clearRect(0, 0, w, h);
        parts.forEach(function (p) {
          p.x += p.vx;
          p.y += p.vy;
          p.vy += 0.06;
          p.rot += p.vr;
          ctx.save();
          ctx.translate(p.x, p.y);
          ctx.rotate((p.rot * Math.PI) / 180);
          ctx.fillStyle = p.color;
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
          ctx.restore();
        });
        if (elapsed < 2200) requestAnimationFrame(frame);
        else canvas.remove();
      }
      requestAnimationFrame(frame);
    },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      SiteSpiderShell.mountSkipLink();
      SiteSpiderShell.mountBrand();
      SiteSpiderShell.initTheme();
      SiteSpiderShell.mountSiteFooter();
    });
  } else {
    SiteSpiderShell.mountSkipLink();
    SiteSpiderShell.mountBrand();
    SiteSpiderShell.initTheme();
    SiteSpiderShell.mountSiteFooter();
  }
})();
