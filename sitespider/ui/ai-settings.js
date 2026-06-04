/** AI 平台下拉（控制台 hidden 欄位 + /ai 設定頁共用） */
(function (global) {
  function providerById(id) {
    return (global.__aiProviders || []).find(function (p) { return p.id === id; });
  }

  var GEMINI_ALIASES = {
    'gemini-pro': 'gemini-2.0-flash',
    'gemini-1.0-pro': 'gemini-2.0-flash',
    'gemini-1.5-flash': 'gemini-2.0-flash',
    'gemini-1.5-pro': 'gemini-2.5-pro',
    'gemini-1.5-flash-8b': 'gemini-2.0-flash',
  };

  function resolveModelForProvider(providerId, model) {
    var m = (model || '').trim();
    if (!m) return { requested: '', resolved: '', remapped: false };
    var pid = (providerId || '').trim().toLowerCase();
    if (pid !== 'google') return { requested: m, resolved: m, remapped: false };
    var low = m.toLowerCase();
    var resolved = GEMINI_ALIASES[low] || m;
    if (low.indexOf('gemini-1.5') === 0 && resolved === m) resolved = 'gemini-2.0-flash';
    return { requested: m, resolved: resolved, remapped: resolved.toLowerCase() !== low };
  }

  function updateModelRemapHint() {
    var hint = document.getElementById('ai-model-remap-hint');
    if (!hint) return;
    var pid = document.getElementById('ai_provider').value;
    var chosen = getSelectedAiModel();
    var r = resolveModelForProvider(pid, chosen);
    if (r.remapped) {
      hint.textContent = '此模型已下線，實際呼叫 API 時會改用 ' + r.resolved + '。';
      hint.classList.remove('hidden');
    } else {
      hint.textContent = '';
      hint.classList.add('hidden');
    }
  }

  function getSelectedAiModel() {
    var sel = document.getElementById('ai_model');
    if (!sel) return '';
    if (sel.value === '__custom__') {
      var c = document.getElementById('ai_model_custom');
      return c ? c.value.trim() : '';
    }
    return sel.value.trim();
  }

  function renderAiProviders(providers, defaultId) {
    global.__aiProviders = providers || [];
    var sel = document.getElementById('ai_provider');
    if (!sel) return;
    sel.innerHTML = '';
    providers.forEach(function (p) {
      var o = document.createElement('option');
      o.value = p.id;
      o.textContent = p.name;
      sel.appendChild(o);
    });
    if (defaultId && providers.some(function (p) { return p.id === defaultId; })) {
      sel.value = defaultId;
    }
    onAiProviderChange();
  }

  function onAiProviderChange(preferredModel) {
    var pid = document.getElementById('ai_provider').value;
    var p = providerById(pid) || {};
    var filter = document.getElementById('ai_model_filter');
    if (filter) filter.value = '';
    var modelSel = document.getElementById('ai_model');
    var customIn = document.getElementById('ai_model_custom');
    var baseRow = document.getElementById('ai_base_url_row');
    var baseIn = document.getElementById('ai_base_url');
    var keyIn = document.getElementById('ai_api_key');
    var docs = document.getElementById('ai-provider-docs');
    if (!modelSel) return;

    modelSel.innerHTML = '';
    (p.models || []).forEach(function (m) {
      var o = document.createElement('option');
      o.value = m;
      o.textContent = m;
      modelSel.appendChild(o);
    });
    var customOpt = document.createElement('option');
    customOpt.value = '__custom__';
    customOpt.textContent = '自訂模型…';
    modelSel.appendChild(customOpt);

    var want = preferredModel || p.default_model;
    if (want && [].some.call(modelSel.options, function (o) { return o.value === want; })) {
      modelSel.value = want;
      if (customIn) customIn.classList.add('hidden');
    } else if (want && customIn) {
      modelSel.value = '__custom__';
      customIn.value = want;
      customIn.classList.remove('hidden');
    } else if (customIn) {
      customIn.classList.add('hidden');
    }

    if (baseRow) baseRow.classList.toggle('hidden', !p.custom_base_url);
    if (baseIn && p.custom_base_url && !baseIn.value) baseIn.placeholder = 'https://your-host/v1';
    if (keyIn && p.key_hint) keyIn.placeholder = p.key_hint + '（僅保存在本機瀏覽器）';
    if (docs) {
      if (p.docs_url) {
        docs.innerHTML = '<a href="' + p.docs_url + '" target="_blank" rel="noopener">取得 API 金鑰 ↗</a>' +
          ' · 共 ' + (p.models || []).length + ' 個模型';
      } else {
        docs.textContent = (p.models || []).length + ' 個模型';
      }
    }
    updateModelRemapHint();
  }

  function filterAiModels() {
    var q = (document.getElementById('ai_model_filter').value || '').toLowerCase();
    var sel = document.getElementById('ai_model');
    [].forEach.call(sel.options, function (o) {
      if (o.value === '__custom__') return;
      o.hidden = q && o.textContent.toLowerCase().indexOf(q) < 0;
    });
  }

  global.SiteSpiderAi = {
    providerById: providerById,
    getSelectedAiModel: getSelectedAiModel,
    resolveModelForProvider: resolveModelForProvider,
    renderAiProviders: renderAiProviders,
    onAiProviderChange: onAiProviderChange,
    filterAiModels: filterAiModels,
    updateModelRemapHint: updateModelRemapHint,
  };
})(window);
