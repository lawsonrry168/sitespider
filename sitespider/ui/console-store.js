/** 控制台設定（localStorage 單一來源，各設定頁與 dashboard 共用） */
(function (global) {
  const STORAGE_KEY = 'sitespider-dashboard-form';
  const DEFAULT_ACCENT = '#6ec9a0';

  function loadAll() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (_) {
      return {};
    }
  }

  function savePartial(partial) {
    try {
      const data = loadAll();
      Object.assign(data, partial);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (_) {}
  }

  function loadBranding() {
    const data = loadAll();
    return {
      consultant_name: (data.consultant_name || '').trim(),
      logo_url: (data.logo_url || '').trim(),
      accent_color: (data.accent_color || '').trim() || DEFAULT_ACCENT,
    };
  }

  function loadWorkspace() {
    const data = loadAll();
    return {
      tenant_id: (data.tenant_id || 'default').trim() || 'default',
      plan_id: (data.plan_id || 'free').trim() || 'free',
      api_key: (data.api_key || '').trim(),
      slack_webhook: (data.slack_webhook || '').trim(),
    };
  }

  function loadAi() {
    const data = loadAll();
    return {
      ai_provider: (data.ai_provider || 'openai').trim(),
      ai_model: (data.ai_model || '').trim(),
      ai_model_custom: (data.ai_model_custom || '').trim(),
      ai_api_key: (data.ai_api_key || data.openai_api_key || '').trim(),
      ai_base_url: (data.ai_base_url || '').trim(),
      auto_ai_polish: !!data.auto_ai_polish,
    };
  }

  function saveLastDelivery(jobId, tenantId, step) {
    if (!jobId) return;
    savePartial({
      last_job_id: String(jobId),
      last_tenant_id: (tenantId || 'default').trim() || 'default',
      last_delivery_step: step || 3,
    });
  }

  function loadLastDelivery() {
    const data = loadAll();
    const jobId = (data.last_job_id || '').trim();
    if (!jobId) return null;
    return {
      job_id: jobId,
      tenant_id: (data.last_tenant_id || 'default').trim() || 'default',
      step: parseInt(data.last_delivery_step, 10) || 3,
    };
  }

  function previewHeaderHtml(b) {
    const brand = b || loadBranding();
    const name = brand.consultant_name || '您的顧問公司';
    const logo = brand.logo_url
      ? '<img src="' + brand.logo_url.replace(/"/g, '&quot;') + '" alt="" class="brand-preview-logo">'
      : '<div class="brand-preview-placeholder">Logo</div>';
    return (
      '<div class="brand-preview-header" style="--preview-accent:' + (brand.accent_color || DEFAULT_ACCENT) + '">' +
      logo +
      '<div><strong>' + name.replace(/</g, '&lt;') + '</strong>' +
      '<p class="brand-preview-sub">SEO 站內稽核交付報告</p></div></div>'
    );
  }

  function applyToDocument() {
    const data = loadAll();
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el && val != null && val !== '') el.value = val;
    };
    const setCheck = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.checked = !!val;
    };
    set('tenant_id', data.tenant_id || 'default');
    set('plan_id', data.plan_id || 'free');
    set('api_key', data.api_key);
    set('slack_webhook', data.slack_webhook);
    set('consultant_name', data.consultant_name);
    set('logo_url', data.logo_url);
    set('accent_color', data.accent_color || DEFAULT_ACCENT);
    set('ai_provider', data.ai_provider);
    set('ai_api_key', data.ai_api_key || data.openai_api_key);
    set('ai_base_url', data.ai_base_url);
    set('ai_model_custom', data.ai_model_custom);
    setCheck('auto_ai_polish', data.auto_ai_polish);
    const picker = document.getElementById('accent_picker');
    if (picker && data.accent_color) picker.value = data.accent_color;
    return data;
  }

  global.ConsoleStore = {
    STORAGE_KEY,
    DEFAULT_ACCENT,
    loadAll,
    savePartial,
    loadBranding,
    loadWorkspace,
    loadAi,
    saveLastDelivery,
    loadLastDelivery,
    previewHeaderHtml,
    applyToDocument,
  };

  global.SiteSpiderBranding = {
    STORAGE_KEY,
    DEFAULT_ACCENT,
    load: loadBranding,
    save: savePartial,
    previewHeaderHtml,
  };
})(window);
