/** 報告頁 / 控制台共用：深淺色切換（localStorage: sitespider-theme） */
(function () {
  var KEY = 'sitespider-theme';

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
      btn.textContent = theme === 'light' ? '◐' : '◑';
      btn.title = theme === 'light' ? '切換深色' : '切換淺色';
      btn.setAttribute('aria-label', btn.title);
    });
  }

  function init() {
    var saved = 'dark';
    try {
      saved = localStorage.getItem(KEY) || 'dark';
    } catch (_) {}
    apply(saved);
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
      if (btn.dataset.ssThemeBound) return;
      btn.dataset.ssThemeBound = '1';
      btn.addEventListener('click', function () {
        var next =
          document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
        try {
          localStorage.setItem(KEY, next);
        } catch (_) {}
        apply(next);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
