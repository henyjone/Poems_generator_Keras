/**
 * NLP Decomposer 前端应用
 */

// ========== 状态管理 ==========
const state = {
    actions: [],           // 所有原子行为
    steps: [],             // 当前计划的步骤
    stepCounter: 0,        // 步骤计数器
    currentFilter: 'all',  // 当前筛选
    searchText: '',        // 搜索文本
};

// ========== DOM 引用 ==========
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    actionList: $('#action-list'),
    actionCount: $('#action-count'),
    actionSearch: $('#action-search'),
    stepsContainer: $('#steps-container'),
    stepsEmpty: $('#steps-empty'),
    resultContent: $('#result-content'),
    modalOverlay: $('#modal-overlay'),
    stepId: $('#step-id'),
    stepAction: $('#step-action'),
    paramsContainer: $('#params-container'),
    paramsFields: $('#params-fields'),
    stepHasCondition: $('#step-has-condition'),
    stepCondition: $('#step-condition'),
    nlInput: $('#nl-input'),
    planPreview: $('#plan-preview'),
    planExplanation: $('#plan-explanation'),
    planSteps: $('#plan-steps'),
};

// ========== API 调用 ==========
async function api(path, data = null) {
    const opts = { headers: { 'Content-Type': 'application/json' } };
    if (data) {
        opts.method = 'POST';
        opts.body = JSON.stringify(data);
    }
    const res = await fetch(`/api${path}`, opts);
    const json = await res.json();
    if (!res.ok) {
        throw new Error(json.error || `HTTP ${res.status}`);
    }
    return json;
}

// ========== 初始化 ==========
async function init() {
    // 加载原子行为列表
    try {
        const data = await api('/actions');
        state.actions = data.actions;
        renderActionList();
        populateActionSelect();
    } catch (e) {
        console.error('加载行为列表失败:', e);
    }

    // 绑定事件
    bindEvents();
}

// ========== 渲染原子行为列表 ==========
function renderActionList() {
    const filtered = state.actions.filter(act => {
        const matchFilter = state.currentFilter === 'all' || act.action_type === state.currentFilter;
        const matchSearch = !state.searchText ||
            act.name.toLowerCase().includes(state.searchText) ||
            act.description.includes(state.searchText);
        return matchFilter && matchSearch;
    });

    dom.actionCount.textContent = filtered.length;

    dom.actionList.innerHTML = filtered.map(act => `
        <div class="action-card" data-action="${act.name}" title="点击添加到计划">
            <div class="action-name">
                <span class="type-badge ${act.action_type}">${act.action_type}</span>
                ${act.name}
            </div>
            <div class="action-desc">${act.description}</div>
            <div class="action-params">
                ${Object.keys(act.parameters).map(p => `<span class="param-chip">${p}</span>`).join('')}
            </div>
        </div>
    `).join('');

    // 点击行为卡片 → 打开添加弹窗
    dom.actionList.querySelectorAll('.action-card').forEach(card => {
        card.addEventListener('click', () => {
            openModal(card.dataset.action);
        });
    });
}

// ========== 填充行为选择下拉 ==========
function populateActionSelect() {
    dom.stepAction.innerHTML = '<option value="">-- 选择原子行为 --</option>' +
        state.actions.map(a => `<option value="${a.name}">${a.name} - ${a.description}</option>`).join('');
}

// ========== 渲染步骤列表 ==========
function renderSteps() {
    if (state.steps.length === 0) {
        dom.stepsEmpty.style.display = 'flex';
        dom.stepsContainer.querySelectorAll('.step-card, .step-connector').forEach(el => el.remove());
        return;
    }

    dom.stepsEmpty.style.display = 'none';

    let html = '';
    state.steps.forEach((step, i) => {
        if (i > 0) {
            html += '<div class="step-connector">&#9660;</div>';
        }
        html += `
            <div class="step-card" data-index="${i}">
                <div class="step-header">
                    <div>
                        <span class="step-id">${step.step_id}</span>
                        <span class="step-action-name">${step.action_name}</span>
                    </div>
                    <button class="step-remove" data-index="${i}" title="移除">&times;</button>
                </div>
                <div class="step-params">${JSON.stringify(step.params)}</div>
                ${step.condition ? `<div class="step-condition">&#9888; 条件: ${step.condition}</div>` : ''}
            </div>
        `;
    });

    // 保留 empty-state 元素，清除其他内容
    const emptyEl = dom.stepsEmpty;
    dom.stepsContainer.innerHTML = '';
    dom.stepsContainer.appendChild(emptyEl);
    dom.stepsContainer.insertAdjacentHTML('beforeend', html);

    // 绑定移除按钮
    dom.stepsContainer.querySelectorAll('.step-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            state.steps.splice(parseInt(btn.dataset.index), 1);
            renderSteps();
        });
    });
}

// ========== 渲染执行结果 ==========
function renderResults(data) {
    let html = '';

    for (const stepId of data.execution_order) {
        if (stepId in data.results) {
            html += `
                <div class="result-item">
                    <div class="result-item-header">
                        <span class="result-step-id">${stepId}</span>
                        <span class="result-status success">SUCCESS</span>
                    </div>
                    <div class="result-value">${formatValue(data.results[stepId])}</div>
                </div>
            `;
        } else if (data.skipped.includes(stepId)) {
            html += `
                <div class="result-item">
                    <div class="result-item-header">
                        <span class="result-step-id">${stepId}</span>
                        <span class="result-status skipped">SKIPPED</span>
                    </div>
                    <div class="result-value" style="color: var(--text-muted)">条件不满足，已跳过</div>
                </div>
            `;
        } else if (stepId in data.errors) {
            html += `
                <div class="result-item">
                    <div class="result-item-header">
                        <span class="result-step-id">${stepId}</span>
                        <span class="result-status error">ERROR</span>
                    </div>
                    <div class="result-value" style="color: var(--danger)">${data.errors[stepId]}</div>
                </div>
            `;
        }
    }

    dom.resultContent.innerHTML = html || '<div class="empty-state"><p>无执行结果</p></div>';
}

function formatValue(val) {
    if (typeof val === 'object') {
        return JSON.stringify(val, null, 2);
    }
    return String(val);
}

// ========== 弹窗控制 ==========
function openModal(actionName = '') {
    state.stepCounter++;
    dom.stepId.value = `step${state.stepCounter}`;

    if (actionName) {
        dom.stepAction.value = actionName;
        onActionSelectChange();
    } else {
        dom.stepAction.value = '';
        dom.paramsContainer.style.display = 'none';
        dom.paramsFields.innerHTML = '';
    }

    dom.stepHasCondition.checked = false;
    dom.stepCondition.style.display = 'none';
    dom.stepCondition.value = '';

    dom.modalOverlay.style.display = 'flex';
}

function closeModal() {
    dom.modalOverlay.style.display = 'none';
}

function onActionSelectChange() {
    const name = dom.stepAction.value;
    const act = state.actions.find(a => a.name === name);

    if (!act || Object.keys(act.parameters).length === 0) {
        dom.paramsContainer.style.display = 'none';
        dom.paramsFields.innerHTML = '';
        return;
    }

    dom.paramsContainer.style.display = 'block';
    dom.paramsFields.innerHTML = Object.entries(act.parameters).map(([key, desc]) => `
        <div class="param-field">
            <label>${key}<br><small style="color:var(--text-muted)">${desc}</small></label>
            <input type="text" class="form-input param-input" data-param="${key}"
                placeholder="${desc}">
        </div>
    `).join('');
}

function confirmAddStep() {
    const stepId = dom.stepId.value.trim();
    const actionName = dom.stepAction.value;

    if (!stepId) {
        alert('请填写步骤 ID');
        return;
    }
    if (!actionName) {
        alert('请选择原子行为');
        return;
    }
    if (state.steps.some(s => s.step_id === stepId)) {
        alert('步骤 ID 已存在，请使用不同的标识');
        return;
    }

    // 收集参数
    const params = {};
    dom.paramsFields.querySelectorAll('.param-input').forEach(input => {
        let val = input.value.trim();
        if (val) {
            // 尝试解析为数字或 JSON
            if (!val.startsWith('$')) {
                try {
                    val = JSON.parse(val);
                } catch {
                    // 保持字符串
                }
            }
            params[input.dataset.param] = val;
        }
    });

    // 条件
    let condition = null;
    if (dom.stepHasCondition.checked && dom.stepCondition.value.trim()) {
        condition = dom.stepCondition.value.trim();
    }

    state.steps.push({
        step_id: stepId,
        action_name: actionName,
        params,
        condition,
    });

    renderSteps();
    closeModal();
}

// ========== 执行计划 ==========
async function executePlan() {
    if (state.steps.length === 0) {
        alert('请先添加步骤');
        return;
    }

    const btn = $('#btn-execute');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 执行中...';

    try {
        const data = await api('/execute', { steps: state.steps });
        renderResults(data);
    } catch (e) {
        dom.resultContent.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon" style="color:var(--danger)">&#10060;</div>
                <p style="color:var(--danger)">${e.message}</p>
            </div>
        `;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#9654; 执行计划';
    }
}

// ========== 自动拆解 ==========
async function decomposeOnly() {
    const text = dom.nlInput.value.trim();
    if (!text) {
        alert('请输入自然语言指令');
        return;
    }

    const btn = $('#btn-decompose-only');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 拆解中...';

    try {
        const data = await api('/decompose', { text });
        showPlanPreview(data.plan);
    } catch (e) {
        alert('拆解失败: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '仅拆解';
    }
}

async function decomposeAndExecute() {
    const text = dom.nlInput.value.trim();
    if (!text) {
        alert('请输入自然语言指令');
        return;
    }

    const btn = $('#btn-decompose-exec');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> 拆解执行中...';

    try {
        const data = await api('/decompose_and_execute', { text });
        showPlanPreview(data.plan);
        renderResults(data);
    } catch (e) {
        alert('执行失败: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '&#9654; 拆解并执行';
    }
}

function showPlanPreview(plan) {
    dom.planPreview.style.display = 'block';
    dom.planExplanation.textContent = plan.explanation || '（无解释）';

    dom.planSteps.innerHTML = plan.steps.map((step, i) => `
        <div class="step-card">
            <div class="step-header">
                <div>
                    <span class="step-id">${step.step_id}</span>
                    <span class="step-action-name">${step.action_name}</span>
                </div>
                <span style="font-size:12px;color:var(--text-muted)">#${i + 1}</span>
            </div>
            <div class="step-params">${JSON.stringify(step.params)}</div>
            ${step.condition ? `<div class="step-condition">&#9888; 条件: ${step.condition}</div>` : ''}
        </div>
        ${i < plan.steps.length - 1 ? '<div class="step-connector">&#9660;</div>' : ''}
    `).join('');
}

// ========== 事件绑定 ==========
function bindEvents() {
    // 筛选标签
    $$('.filter-tags .tag').forEach(tag => {
        tag.addEventListener('click', () => {
            $$('.filter-tags .tag').forEach(t => t.classList.remove('active'));
            tag.classList.add('active');
            state.currentFilter = tag.dataset.filter;
            renderActionList();
        });
    });

    // 搜索
    dom.actionSearch.addEventListener('input', (e) => {
        state.searchText = e.target.value.toLowerCase();
        renderActionList();
    });

    // 模式切换
    $$('.mode-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            $$('.mode-tab').forEach(t => t.classList.remove('active'));
            $$('.mode-content').forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            $(`#mode-${tab.dataset.mode}`).classList.add('active');
        });
    });

    // 添加步骤
    $('#btn-add-step').addEventListener('click', () => openModal());
    $('#btn-clear-steps').addEventListener('click', () => {
        state.steps = [];
        state.stepCounter = 0;
        renderSteps();
    });

    // 弹窗
    $('#modal-close').addEventListener('click', closeModal);
    $('#btn-modal-cancel').addEventListener('click', closeModal);
    $('#btn-modal-confirm').addEventListener('click', confirmAddStep);
    dom.modalOverlay.addEventListener('click', (e) => {
        if (e.target === dom.modalOverlay) closeModal();
    });

    // 行为选择变更
    dom.stepAction.addEventListener('change', onActionSelectChange);

    // 条件勾选
    dom.stepHasCondition.addEventListener('change', () => {
        dom.stepCondition.style.display = dom.stepHasCondition.checked ? 'block' : 'none';
    });

    // 执行
    $('#btn-execute').addEventListener('click', executePlan);

    // 自动拆解
    $('#btn-decompose-only').addEventListener('click', decomposeOnly);
    $('#btn-decompose-exec').addEventListener('click', decomposeAndExecute);

    // 清空结果
    $('#btn-clear-results').addEventListener('click', () => {
        dom.resultContent.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">&#9881;</div>
                <p>执行计划后结果将显示在这里</p>
            </div>
        `;
    });

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

// ========== 启动 ==========
document.addEventListener('DOMContentLoaded', init);
