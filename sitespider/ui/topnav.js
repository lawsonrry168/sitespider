/** 共用頂欄導覽（主選單 + 更多下拉） */
(function (global) {
  var HOME = '/';

  var PRIMARY = [
    { href: '/', label: '爬取中心', id: 'console' },
    { href: '/demo', label: '範例報告', id: 'demo' },
    { href: '/guide', label: '使用說明', id: 'guide' },
    { href: '/pricing', label: '方案價格', id: 'pricing' },
    { href: '/ai', label: 'AI 文案', id: 'ai' },
  ];

  var MORE = [
    { href: '/workspace', label: '帳號與方案', id: 'workspace' },
    { href: '/branding', label: '報告品牌', id: 'branding' },
    { href: '/sites', label: '多站儀表板', id: 'sites' },
    { href: '/about', label: '關於我們', id: 'about' },
    { href: '/contact', label: '聯絡我們', id: 'contact' },
    { href: '/admin', label: '營運後台', id: 'admin' },
  ];

  var LINKS = PRIMARY.concat(MORE);

  function shouldShowBack(activeId) {
    if (activeId !== 'console') return true;
    try {
      var ref = document.referrer || '';
      return !!(ref && ref.indexOf(location.origin) === 0 && ref.replace(/\/$/, '') !== location.origin);
    } catch (_) {
      return false;
    }
  }

  function navAnchor(nav) {
    return nav.querySelector('.theme-toggle') || null;
  }

  function ensureBackButton(nav, activeId) {
    var existing = nav.querySelector('.nav-back');
    if (!shouldShowBack(activeId)) {
      if (existing) existing.remove();
      return;
    }
    var btn = existing;
    if (!btn) {
      btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'nav-back';
      btn.textContent = '← 返回';
      btn.title = '返回上一頁';
      btn.setAttribute('aria-label', '返回上一頁');
      var before = navAnchor(nav);
      if (before) nav.insertBefore(btn, before);
      else nav.insertBefore(btn, nav.firstChild);
    }
    btn.onclick = function () {
      if (global.SiteSpiderBack && global.SiteSpiderBack.goBack) {
        global.SiteSpiderBack.goBack(HOME);
      } else {
        location.href = HOME;
      }
    };
  }

  function closeAllMoreMenus() {
    document.querySelectorAll('.nav-more.is-open').forEach(function (el) {
      el.classList.remove('is-open');
      var btn = el.querySelector('.nav-more-toggle');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    });
  }

  function consoleHomeLink() {
    var path = location.pathname || '';
    if (path.indexOf('/reports/') >= 0) {
      if (global.SiteSpiderBack && global.SiteSpiderBack.consoleHomeHref) {
        return global.SiteSpiderBack.consoleHomeHref();
      }
    }
    return '/?step=1';
  }

  function linkEl(l, activeId) {
    var a = document.createElement('a');
    if (l.id === 'console') {
      a.href = consoleHomeLink();
    } else {
      a.href = l.href;
    }
    a.textContent = l.label;
    a.dataset.ssLink = '1';
    a.setAttribute('role', 'menuitem');
    if (l.id === activeId) {
      a.className = 'nav-active';
      a.setAttribute('aria-current', 'page');
    }
    return a;
  }

  function ensureMoreMenu(nav, activeId) {
    var existing = nav.querySelector('.nav-more');
    if (existing) existing.remove();

    var inMore = MORE.some(function (l) { return l.id === activeId; });
    var wrap = document.createElement('div');
    wrap.className = 'nav-more' + (inMore ? ' nav-more--active' : '');

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'nav-more-toggle';
    toggle.textContent = '更多 ▾';
    toggle.setAttribute('aria-haspopup', 'true');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-controls', 'nav-more-menu');

    var menu = document.createElement('div');
    menu.className = 'nav-more-menu';
    menu.id = 'nav-more-menu';
    menu.setAttribute('role', 'menu');
    MORE.forEach(function (l) {
      menu.appendChild(linkEl(l, activeId));
    });

    toggle.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      var open = !wrap.classList.contains('is-open');
      closeAllMoreMenus();
      if (open) {
        wrap.classList.add('is-open');
        toggle.setAttribute('aria-expanded', 'true');
      } else {
        toggle.setAttribute('aria-expanded', 'false');
      }
    });

    menu.addEventListener('click', function (e) {
      e.stopPropagation();
    });

    wrap.appendChild(toggle);
    wrap.appendChild(menu);
    var before = navAnchor(nav);
    if (before) nav.insertBefore(wrap, before);
    else nav.appendChild(wrap);
  }

  function render(activeId) {
    document.querySelectorAll('nav.topnav[data-ss-nav]').forEach(function (nav) {
      ensureBackButton(nav, activeId);
      nav.querySelectorAll('a[data-ss-link], .nav-more').forEach(function (el) { el.remove(); });

      var before = navAnchor(nav);
      PRIMARY.forEach(function (l) {
        var a = linkEl(l, activeId);
        a.removeAttribute('role');
        if (before) nav.insertBefore(a, before);
        else nav.appendChild(a);
      });
      ensureMoreMenu(nav, activeId);
    });
  }

  if (!global.__ssNavMoreBound) {
    global.__ssNavMoreBound = true;
    document.addEventListener('click', function (e) {
      if (e.target.closest('.nav-more')) return;
      closeAllMoreMenus();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeAllMoreMenus();
    });
  }

  global.SiteSpiderNav = { render: render, LINKS: LINKS, PRIMARY: PRIMARY, MORE: MORE };
})(window);
