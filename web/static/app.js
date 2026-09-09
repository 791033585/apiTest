const state = { specId: null, interfaces: [], currentOperationId: null, cases: [], selectedCaseId: null };

const $ = (id) => document.getElementById(id);
const status = (message, kind = '') => { $('status').textContent = message; $('status').className = `status ${kind}`; };
const jsonText = (value) => JSON.stringify(value ?? {}, null, 2);
const parseJson = (value, fallback = {}) => { try { return value.trim() ? JSON.parse(value) : fallback; } catch { throw new Error('JSON 格式不正确'); } };

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `请求失败: ${response.status}`);
  return payload;
}

function renderInterfaces() {
  $('spec-title').textContent = state.specId ? '当前 OpenAPI' : '尚未上传';
  $('interface-count').textContent = state.interfaces.length;
  const list = $('interface-list');
  if (!state.interfaces.length) { list.className = 'interface-list empty-state'; list.textContent = '上传 Swagger 后显示接口'; return; }
  list.className = 'interface-list';
  list.innerHTML = state.interfaces.map(item => `
    <button class="interface-item ${item.operation_id === state.currentOperationId ? 'active' : ''}" data-operation="${escapeHtml(item.operation_id)}">
      <span class="method">${escapeHtml(item.method)}</span><span class="path">${escapeHtml(item.path)}</span>
      <span class="summary">${escapeHtml(item.summary || item.operation_id)}</span>
    </button>`).join('');
  list.querySelectorAll('[data-operation]').forEach(button => button.addEventListener('click', () => selectInterface(button.dataset.operation)));
}

function renderCases() {
  $('selected-interface').textContent = state.currentOperationId || '选择一个接口';
  $('case-count').textContent = state.cases.length;
  $('select-all-button').disabled = !state.cases.length;
  $('run-button').disabled = !state.cases.some(item => item.enabled !== false);
  const list = $('case-list');
  if (!state.cases.length) { list.className = 'case-list empty-state'; list.textContent = '暂无用例，点击顶部 AI 生成用例'; return; }
  list.className = 'case-list';
  list.innerHTML = state.cases.map(item => `
    <div class="case-row ${item.case_id === state.selectedCaseId ? 'active' : ''}">
      <input type="checkbox" class="case-check" data-case-id="${escapeHtml(item.case_id)}" ${item.enabled === false ? '' : 'checked'}>
      <div class="case-title" data-edit="${escapeHtml(item.case_id)}"><strong>${escapeHtml(item.title)}</strong><span class="case-id">${escapeHtml(item.case_id)}</span></div>
      <span class="pill ${escapeHtml(item.case_type || '')}">${escapeHtml(item.case_type || '-')}</span>
      <span class="pill">${escapeHtml(item.priority || '-')}</span>
      <button class="edit-button" data-edit="${escapeHtml(item.case_id)}">编辑</button>
    </div>`).join('');
  list.querySelectorAll('[data-edit]').forEach(element => element.addEventListener('click', () => editCase(element.dataset.edit)));
}

function editCase(caseId) {
  const item = state.cases.find(caseItem => caseItem.case_id === caseId);
  if (!item) return;
  state.selectedCaseId = caseId;
  $('editor-empty').classList.add('hidden'); $('case-form').classList.remove('hidden');
  $('case-id').value = item.case_id; $('case-title').value = item.title || '';
  $('case-type').value = item.case_type || ''; $('case-priority').value = item.priority || '';
  $('case-headers').value = jsonText(item.headers); $('case-params').value = jsonText(item.params); $('case-data').value = jsonText(item.data);
  $('case-json').value = jsonText(item.json); $('case-assertions').value = jsonText(item.assertions || []);
  $('case-extracts').value = jsonText(item.extracts || []); $('case-depends').value = jsonText(item.depends_on || []);
  $('case-enabled').checked = item.enabled !== false; $('case-notes').value = item.notes || '';
  renderCases();
}

async function selectInterface(operationId) {
  state.currentOperationId = operationId; state.selectedCaseId = null; renderInterfaces();
  try { const payload = await api(`/api/interfaces/${encodeURIComponent(operationId)}/cases`); state.cases = payload.cases || []; renderCases(); clearEditor(); status(`已选择 ${operationId}`, 'ok'); }
  catch (error) { status(error.message, 'error'); }
}

function clearEditor() { $('editor-empty').classList.remove('hidden'); $('case-form').classList.add('hidden'); }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]); }

$('spec-file').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  const formData = new FormData(); formData.append('file', file); status('正在解析 OpenAPI...');
  try {
    const response = await fetch('/api/specs/upload', { method: 'POST', body: formData });
    const payload = await response.json(); if (!response.ok) throw new Error(payload.detail || '上传失败');
    state.specId = payload.spec_id; state.interfaces = payload.interfaces || []; state.currentOperationId = null; state.cases = [];
    renderInterfaces(); renderCases(); clearEditor(); $('generate-button').disabled = true; status(`已解析 ${state.interfaces.length} 个接口`, 'ok');
  } catch (error) { status(error.message, 'error'); }
});

$('generate-button').addEventListener('click', async () => {
  if (!state.currentOperationId) return;
  $('generate-button').disabled = true; status('AI 正在生成当前接口用例，请稍候...');
  try {
    const payload = await api(`/api/interfaces/${encodeURIComponent(state.currentOperationId)}/generate`, { method: 'POST', body: JSON.stringify({ max_cases: 20 }) });
    state.cases = payload.cases || []; renderCases(); clearEditor(); status(`已生成 ${state.cases.length} 条用例`, 'ok');
  } catch (error) { status(error.message, 'error'); }
  finally { $('generate-button').disabled = false; }
});

$('select-all-button').addEventListener('click', () => {
  const checks = [...document.querySelectorAll('.case-check')]; const shouldCheck = checks.some(input => !input.checked);
  checks.forEach(input => { input.checked = shouldCheck; });
});

$('case-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const payload = {
      title: $('case-title').value, headers: parseJson($('case-headers').value), params: parseJson($('case-params').value), data: parseJson($('case-data').value),
      json: parseJson($('case-json').value), assertions: parseJson($('case-assertions').value, []), extracts: parseJson($('case-extracts').value, []),
      depends_on: parseJson($('case-depends').value, []), enabled: $('case-enabled').checked, notes: $('case-notes').value,
    };
    const updated = await api(`/api/cases/${encodeURIComponent($('case-id').value)}`, { method: 'PUT', body: JSON.stringify(payload) });
    state.cases = state.cases.map(item => item.case_id === updated.case_id ? updated : item); renderCases(); status('用例已保存', 'ok');
  } catch (error) { status(error.message, 'error'); }
});

$('delete-button').addEventListener('click', async () => {
  const caseId = $('case-id').value; if (!caseId || !confirm('确认删除这条用例？')) return;
  try { await api(`/api/cases/${encodeURIComponent(caseId)}`, { method: 'DELETE' }); state.cases = state.cases.filter(item => item.case_id !== caseId); state.selectedCaseId = null; clearEditor(); renderCases(); status('用例已删除', 'ok'); }
  catch (error) { status(error.message, 'error'); }
});

$('run-button').addEventListener('click', async () => {
  const selected = [...document.querySelectorAll('.case-check:checked')].map(input => input.dataset.caseId);
  if (!selected.length) { status('请至少勾选一条启用用例', 'error'); return; }
  try {
    const payload = { case_ids: selected, base_url: $('base-url').value.trim(), headers: parseJson($('global-headers').value), variables: parseJson($('variables').value) };
    $('run-button').disabled = true; status('正在执行选中用例，请稍候...');
    const result = await api('/api/runs', { method: 'POST', body: JSON.stringify(payload) });
    $('metric-total').textContent = result.total; $('metric-passed').textContent = result.passed; $('metric-failed').textContent = result.failed; $('metric-duration').textContent = `${result.duration}s`;
    $('run-output').textContent = result.output || '无输出'; $('report-link').href = result.report_url || result.allure_results_url || '#'; $('report-link').classList.remove('hidden');
    status(result.failed ? `执行完成，${result.failed} 条失败` : '执行完成，全部通过', result.failed ? 'error' : 'ok');
  } catch (error) { status(error.message, 'error'); }
  finally { $('run-button').disabled = false; }
});

document.addEventListener('click', event => { if (event.target.closest('.interface-item') && state.currentOperationId) $('generate-button').disabled = false; });

async function loadCurrentSpec() {
  try {
    const payload = await api('/api/interfaces');
    state.specId = payload.spec_id; state.interfaces = payload.interfaces || [];
    renderInterfaces(); status(`已恢复 ${state.interfaces.length} 个接口`, 'ok');
  } catch (error) {
    if (!String(error.message).includes('尚未上传')) status(error.message, 'error');
  }
}

renderInterfaces(); renderCases(); loadCurrentSpec();
