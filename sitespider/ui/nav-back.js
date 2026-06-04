/** 返回上一頁；無同站瀏覽紀錄時改導向 fallback */
(function (global) {
  function goBack(fallback) {
    var fb = fallback || '/';
    var home = consoleHomeHref();
    if (fb === '/' || fb === home) {
      location.href = home;
      return;
    }
    try {
      var ref = document.referrer || '';
      if (history.length > 1 && ref && ref.indexOf(location.origin) === 0 && ref.indexOf('/reports/') < 0) {
        history.back();
        return;
      }
    } catch (_) {}
    location.href = fb;
  }

  function mount(el) {
    if (!el || el.dataset.ssBackBound) return;
    el.dataset.ssBackBound = '1';
    el.addEventListener('click', function (e) {
      e.preventDefault();
      goBack(el.getAttribute('data-fallback') || '/');
    });
  }

  function homeUrl(tenant, job) {
    return '/?tenant=' + encodeURIComponent(tenant) + '&job=' + encodeURIComponent(job) + '&step=3';
  }

  function consoleHomeHref() {
    var path = location.pathname || '';
    if (path.indexOf('/reports/') >= 0) {
      if (typeof window.__SS_CONSOLE_HOME === 'string' && window.__SS_CONSOLE_HOME) {
        return window.__SS_CONSOLE_HOME;
      }
      var parts = path.split('/').filter(Boolean);
      var i = parts.indexOf('reports');
      if (i >= 0) {
        var rest = parts.slice(i + 1);
        if (rest.length === 1) {
          return homeUrl('default', rest[0]);
        }
        if (rest.length === 2 && /\./.test(rest[1])) {
          return homeUrl('default', rest[0]);
        }
        if (rest.length >= 2 && !/\./.test(rest[1])) {
          return homeUrl(rest[0], rest[1]);
        }
      }
    }
    return '/?step=1';
  }

  function fixConsoleHomeLinks() {
    var href = consoleHomeHref();
    document.querySelectorAll('a.report-brand-home, a.ss-console-home').forEach(function (a) {
      a.setAttribute('href', href);
      a.setAttribute('title', '返回爬取中心');
    });
    document.querySelectorAll('.report-brand-block').forEach(function (el) {
      if (el.closest('a.report-brand-home')) return;
      el.style.cursor = 'pointer';
      el.setAttribute('title', '返回爬取中心');
      el.addEventListener('click', function (ev) {
        if (ev.target.closest('a')) return;
        location.href = href;
      });
    });
  }

  function mountAll() {
    document.querySelectorAll('[data-ss-back]').forEach(mount);
    fixConsoleHomeLinks();
  }

  global.SiteSpiderBack = { goBack: goBack, mount: mount, mountAll: mountAll, consoleHomeHref: consoleHomeHref };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountAll);
  } else {
    mountAll();
  }
})(window);
