/**
 * SiteSpider 桌面 GUI — 爬取中心三欄、其他控制台頁寬版、右欄拖曳、desktop=1 連結。
 */
(function (global) {
  var STORAGE_LAYOUT = 'sitespider-desktop-layout';
  var STORAGE_RAIL_W = 'sitespider-rail-width';
  var MIN_WIDTH = 1100;
  var RAIL_MIN = 280;
  var RAIL_MAX = 520;
  var RAIL_DEFAULT = 360;
  var railHome = null;
  var dragging = false;

  function preferDesktop() {
    try {
      if (global.location.search.indexOf('desktop=0') >= 0) return false;
      if (global.location.search.indexOf('desktop=1') >= 0) return true;
      if (localStorage.getItem(STORAGE_LAYOUT) === '1') return true;
    } catch (_) {}
    return false;
  }

  function isConsoleApp() {
    return !!(document.body && document.body.classList.contains('app-console'));
  }

  function isDashboard() {
    var p = global.location.pathname || '';
    return p === '/' || p === '/dashboard' || p === '/dashboard.html';
  }

  function viewportDesktop() {
    try {
      return global.matchMedia('(min-width: ' + MIN_WIDTH + 'px)').matches;
    } catch (_) {
      return global.innerWidth >= MIN_WIDTH;
    }
  }

  function shouldUseDesktop() {
    if (!isConsoleApp()) return false;
    return preferDesktop() || viewportDesktop();
  }

  function withDesktopParam(href) {
    if (!href || href.charAt(0) !== '/' || href.indexOf('desktop=') >= 0) return href;
    return href + (href.indexOf('?') >= 0 ? '&' : '?') + 'desktop=1';
  }

  function normalizePath(p) {
    p = (p || '/').replace(/\/+$/, '') || '/';
    return p.replace(/\.html$/i, '') || '/';
  }

  function navItemActive(item) {
    var p = normalizePath(global.location.pathname);
    var h = normalizePath(item.href);
    if (item.id === 'console') return p === '/' || p === '/dashboard';
    if (h === '/') return p === '/';
    return p === h;
  }

  function createSidebar(includeWorkflow) {
    var aside = document.createElement('aside');
    aside.className = 'ss-desktop-sidebar';
    aside.setAttribute('aria-label', '應用程式導覽');
    aside.innerHTML =
      '<div class="ss-sidebar-brand">' +
      '<div class="brand-icon" data-brand title="返回爬取中心"></div>' +
      '<div><p class="ss-sidebar-title">SiteSpider</p>' +
      '<p class="ss-sidebar-sub">SEO · GEO 交付</p></div></div>' +
      '<nav class="ss-sidebar-nav" id="ss-sidebar-nav" aria-label="主選單"></nav>' +
      (includeWorkflow
        ? '<p class="ss-sidebar-section-label">工作流程</p>' +
          '<div class="ss-sidebar-workflow" id="ss-sidebar-workflow-slot" aria-label="工作流程"></div>'
        : '') +
      '<nav class="ss-sidebar-more" id="ss-sidebar-more" aria-label="更多功能"></nav>' +
      '<div class="ss-sidebar-spacer" aria-hidden="true"></div>' +
      '<a href="/guide" class="ss-sidebar-guide">使用說明</a>';
    return aside;
  }

  function mountSidebarNav() {
    var primary = document.getElementById('ss-sidebar-nav');
    var more = document.getElementById('ss-sidebar-more');
    if (!primary || !global.SiteSpiderNav) return;
    if (primary.dataset.mounted === '1') return;
    primary.dataset.mounted = '1';
    if (more) more.dataset.mounted = '1';

    function addLink(parent, item) {
      var a = document.createElement('a');
      a.href = withDesktopParam(item.href);
      a.textContent = item.label;
      if (navItemActive(item)) {
        a.className = 'is-active';
        a.setAttribute('aria-current', 'page');
      }
      parent.appendChild(a);
    }

    (global.SiteSpiderNav.PRIMARY || []).forEach(function (item) {
      if (item.id === 'console') return;
      addLink(primary, item);
    });
    if (more) {
      (global.SiteSpiderNav.MORE || []).forEach(function (item) {
        addLink(more, item);
      });
    }
    var guide = document.querySelector('.ss-sidebar-guide');
    if (guide) guide.href = withDesktopParam('/guide');
  }

  function wireSidebarBrand() {
    document.querySelectorAll('.ss-sidebar-brand').forEach(function (block) {
      if (block.dataset.wired) return;
      block.dataset.wired = '1';
      block.setAttribute('role', 'link');
      block.setAttribute('tabindex', '0');
      block.setAttribute('title', '返回爬取中心');
      function go() {
        global.location.href = withDesktopParam('/');
      }
      block.addEventListener('click', go);
      block.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          go();
        }
      });
    });
  }

  function wrapSecondaryPage() {
    if (document.getElementById('ss-frame') || isDashboard()) return;
    var body = document.body;
    var frame = document.createElement('div');
    frame.className = 'ss-frame';
    frame.id = 'ss-frame';
    var sidebar = createSidebar(false);
    var workspace = document.createElement('div');
    workspace.className = 'ss-workspace ss-workspace--page';
    var scripts = [];
    Array.from(body.children).forEach(function (ch) {
      if (ch.tagName === 'SCRIPT' || ch.id === 'ss-toast-host') scripts.push(ch);
      else if (ch !== frame) workspace.appendChild(ch);
    });
    frame.appendChild(sidebar);
    frame.appendChild(workspace);
    body.insertBefore(frame, body.firstChild);
    scripts.forEach(function (s) {
      body.appendChild(s);
    });
    mountSidebarNav();
    wireSidebarBrand();
    if (global.SiteSpiderShell && SiteSpiderShell.mountBrand) SiteSpiderShell.mountBrand();
  }

  function relocateWorkflowRail(desktopOn) {
    if (!isDashboard()) return;
    var rail = document.querySelector('.console-context .step-rail.pipeline');
    var slot = document.getElementById('ss-sidebar-workflow-slot');
    if (!rail || !slot) return;
    if (!railHome) railHome = rail.parentElement;
    if (desktopOn) {
      if (rail.parentElement !== slot) {
        rail.classList.add('ss-sidebar-pipeline');
        slot.appendChild(rail);
      }
    } else if (railHome && rail.parentElement !== railHome) {
      rail.classList.remove('ss-sidebar-pipeline');
      railHome.insertBefore(rail, railHome.firstChild);
    }
  }

  function loadRailWidth() {
    try {
      var n = parseInt(localStorage.getItem(STORAGE_RAIL_W), 10);
      if (n >= RAIL_MIN && n <= RAIL_MAX) return n;
    } catch (_) {}
    return RAIL_DEFAULT;
  }

  function applyRailWidth(px) {
    document.documentElement.style.setProperty('--ss-rail-w', px + 'px');
    try {
      localStorage.setItem(STORAGE_RAIL_W, String(px));
    } catch (_) {}
  }

  function mountRailResizer() {
    if (!isDashboard()) return;
    var layout = document.querySelector('.layout-console-v3');
    var rail = document.querySelector('.sidebar-rail');
    if (!layout || !rail) return;
    applyRailWidth(loadRailWidth());
    var handle = document.getElementById('ss-rail-resizer');
    if (!handle) {
      handle = document.createElement('div');
      handle.id = 'ss-rail-resizer';
      handle.className = 'ss-rail-resizer';
      handle.setAttribute('role', 'separator');
      handle.setAttribute('aria-orientation', 'vertical');
      handle.setAttribute('aria-label', '拖曳調整右側欄寬度');
      handle.setAttribute('tabindex', '0');
      layout.insertBefore(handle, rail);
    }
    if (handle.dataset.wired === '1') return;
    handle.dataset.wired = '1';

    function onMove(clientX) {
      var rect = layout.getBoundingClientRect();
      var w = Math.round(rect.right - clientX);
      w = Math.max(RAIL_MIN, Math.min(RAIL_MAX, w));
      applyRailWidth(w);
    }

    handle.addEventListener('mousedown', function (e) {
      e.preventDefault();
      dragging = true;
      document.body.classList.add('ss-rail-dragging');
    });
    handle.addEventListener('keydown', function (e) {
      var cur = loadRailWidth();
      if (e.key === 'ArrowLeft') {
        applyRailWidth(Math.max(RAIL_MIN, cur - 16));
        e.preventDefault();
      }
      if (e.key === 'ArrowRight') {
        applyRailWidth(Math.min(RAIL_MAX, cur + 16));
        e.preventDefault();
      }
    });

    global.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      onMove(e.clientX);
    });
    global.addEventListener('mouseup', function () {
      if (!dragging) return;
      dragging = false;
      document.body.classList.remove('ss-rail-dragging');
    });
  }

  function updateStatusFromStep() {
    var bar = document.getElementById('ss-status-text');
    var main = document.getElementById('main-content');
    if (!bar || !main) return;
    var step = main.getAttribute('data-console-step') || '1';
    var title = document.getElementById('context-title');
    var sub = document.getElementById('context-sub');
    var t = title ? title.textContent : '';
    var s = sub ? sub.textContent : '';
    bar.textContent = '步驟 ' + step + '/3' + (t ? ' · ' + t : '') + (s ? ' — ' + s : '');
  }

  function watchStepChanges() {
    var main = document.getElementById('main-content');
    if (!main || main.dataset.ssDesktopWatch) return;
    main.dataset.ssDesktopWatch = '1';
    new MutationObserver(updateStatusFromStep).observe(main, {
      attributes: true,
      attributeFilter: ['data-console-step'],
    });
    ['context-title', 'context-sub'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) {
        new MutationObserver(updateStatusFromStep).observe(el, {
          childList: true,
          characterData: true,
          subtree: true,
        });
      }
    });
  }

  function syncKbdLabels() {
    var mod = document.getElementById('kbd-mod');
    var bar = document.getElementById('ss-kbd-mod-bar');
    if (mod && bar) bar.textContent = mod.textContent;
  }

  function wireInternalLinks() {
    if (document.body.dataset.ssDesktopLinks) return;
    document.body.dataset.ssDesktopLinks = '1';
    document.addEventListener(
      'click',
      function (e) {
        if (!document.documentElement.classList.contains('ss-desktop')) return;
        var a = e.target.closest('a[href^="/"]');
        if (!a || a.target === '_blank' || a.hasAttribute('download')) return;
        var href = a.getAttribute('href');
        if (!href || href.indexOf('desktop=') >= 0) return;
        if (href.indexOf('#') === 0) return;
        a.setAttribute('href', withDesktopParam(href.split('#')[0]) + (href.indexOf('#') >= 0 ? href.slice(href.indexOf('#')) : ''));
      },
      true
    );
  }

  function setDesktop(on) {
    document.documentElement.classList.toggle('ss-desktop', !!on);
    try {
      if (on) localStorage.setItem(STORAGE_LAYOUT, '1');
    } catch (_) {}
    if (!on) {
      relocateWorkflowRail(false);
      return;
    }
    wireSidebarBrand();
    wireInternalLinks();
    if (isDashboard()) {
      mountSidebarNav();
      relocateWorkflowRail(true);
      mountRailResizer();
      updateStatusFromStep();
    } else {
      wrapSecondaryPage();
    }
  }

  function init() {
    if (!isConsoleApp()) return;
    if (isDashboard()) {
      watchStepChanges();
      syncKbdLabels();
    }
    setDesktop(shouldUseDesktop());
    var mq;
    try {
      mq = global.matchMedia('(min-width: ' + MIN_WIDTH + 'px)');
    } catch (_) {}
    var onChange = function () {
      setDesktop(shouldUseDesktop());
    };
    if (mq && mq.addEventListener) mq.addEventListener('change', onChange);
    else global.addEventListener('resize', onChange);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  global.SiteSpiderDesktop = {
    enable: function () {
      setDesktop(true);
    },
    disable: function () {
      try {
        localStorage.setItem(STORAGE_LAYOUT, '0');
      } catch (_) {}
      setDesktop(false);
    },
    isActive: function () {
      return document.documentElement.classList.contains('ss-desktop');
    },
    setRailWidth: applyRailWidth,
  };
})(window);
