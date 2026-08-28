// Captura OCR Local - frontend SPA (sin frameworks, vanilla JS)
const $ = (s) => document.querySelector(s);
const api = "/api/v1";
let selectedJob = null;
let sse = null;
let fieldLabelsCache = {};

// Operator config (Feature 11)
let operatorConfig = null;
const OPERATOR_STORAGE_KEY = "gi_ocr_operator";

function getAuthHeaders() {
  if (!operatorConfig) return {};
  return {
    "X-Operator-Id": operatorConfig.id,
    "X-Operator-Role": operatorConfig.role,
  };
}

function loadOperatorConfig() {
  const stored = localStorage.getItem(OPERATOR_STORAGE_KEY);
  if (stored) {
    try {
      operatorConfig = JSON.parse(stored);
      return true;
    } catch (_) {}
  }
  return false;
}

function saveOperatorConfig(config) {
  operatorConfig = config;
  localStorage.setItem(OPERATOR_STORAGE_KEY, JSON.stringify(config));
  updateOperatorBadge();
}

function updateOperatorBadge() {
  const badge = $("#operator-badge");
  if (badge && operatorConfig) {
    badge.textContent = `${operatorConfig.id} (${operatorConfig.role})`;
    badge.className = "badge " + operatorConfig.role;
  }
}

function showOperatorModal() {
  const modal = $("#operator-modal");
  if (modal) modal.style.display = "flex";
}

function hideOperatorModal() {
  const modal = $("#operator-modal");
  if (modal) modal.style.display = "none";
}

function setupOperatorModal() {
  const form = $("#operator-form");
  const idInput = $("#operator-id");
  const roleSelect = $("#operator-role");
  const cancelBtn = $("#operator-cancel");
  
  if (operatorConfig) {
    idInput.value = operatorConfig.id;
    roleSelect.value = operatorConfig.role;
  }
  
  form.onsubmit = (e) => {
    e.preventDefault();
    const id = idInput.value.trim();
    const role = roleSelect.value;
    if (!id || !role) return;
    saveOperatorConfig({ id, role });
    hideOperatorModal();
  };
  
  cancelBtn.onclick = () => {
    if (!operatorConfig) {
      alert("Debe configurar operador para continuar");
      return;
    }
    hideOperatorModal();
  };
}

// ---- utilidades ----
const fmt = (s) => (s == null ? "" : String(s));
function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}
async function jget(url) {
  const r = await fetch(url, { headers: getAuthHeaders() });
  if (!r.ok) throw new Error((await r.text()) || r.status);
  return r.json();
}
async function jpost(url, body) {
  const r = await fetch(url, { 
    method: "POST", 
    headers: { "Content-Type": "application/json", ...getAuthHeaders() }, 
    body: JSON.stringify(body || {}) 
  });
  if (!r.ok) throw new Error((await r.text()) || r.status);
  return r.json();
}

// ---- uploads ----
const dropzone = $("#dropzone");
const fileInput = $("#file-input");
const camInput = $("#cam-input");
const dirInput = $("#dir-input");

$("#pick-btn").onclick = () => fileInput.click();
$("#cam-btn").onclick = () => camInput.click();
$("#dir-btn").onclick = () => dirInput.click();
fileInput.onchange = () => upload(fileInput.files);
camInput.onchange = () => upload(camInput.files);
dirInput.onchange = () => upload(dirInput.files);

;["dragenter", "dragover"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("drag"); })
);
;["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("drag"); })
);
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer && e.dataTransfer.files) upload(e.dataTransfer.files);
});

async function upload(fileList) {
  const msg = $("#upload-msg");
  msg.className = "msg";
  if (!fileList || !fileList.length) { msg.textContent = "No se seleccionaron archivos."; return; }
  const fd = new FormData();
  for (const f of fileList) fd.append("files", f, f.name);
  msg.textContent = `Enviando ${fileList.length} archivo(s)...`;
  try {
    const r = await fetch(api + "/jobs", { method: "POST", body: fd, headers: getAuthHeaders() });
    const data = await r.json();
    if (!r.ok) throw new Error(JSON.stringify(data));
    msg.className = "msg ok";
    msg.textContent = `Encolados: ${data.queued} documento(s).`;
    refresh();
  } catch (e) {
    msg.className = "msg err";
    msg.textContent = "Error al subir: " + e.message;
  }
}

// ---- cola ----
$("#refresh-btn").onclick = refresh;
async function refresh() {
  try {
    const data = await jget(api + "/jobs");
    renderQueue(data.jobs || []);
  } catch (e) {
    $("#queue").innerHTML = '<div class="empty">No se pudo cargar la cola.</div>';
  }
}
function stats(jobs) {
  const c = (st) => jobs.filter((j) => j.status === st).length;
  $("#stat-queued").textContent = `${c("queued") + c("processing")} en cola`;
  $("#stat-ready").textContent = `${c("ready") + c("confirmed")} listos`;
  $("#stat-failed").textContent = `${c("failed")} fallidos`;
  const statQuality = $("#stat-quality");
  if (statQuality) statQuality.textContent = `${c("needs_new_photo")} requieren nueva foto`;
}
function renderQueue(jobs) {
  stats(jobs);
  const q = $("#queue");
  q.innerHTML = "";
  if (!jobs.length) {
    q.appendChild(el("div", "empty", "Sin documentos. Cargá uno para empezar."));
    return;
  }
  jobs.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""));
  for (const j of jobs) {
    const it = el("div", "qitem" + (selectedJob === j.job_id ? " active" : ""));
    it.onclick = () => { selectedJob = j.job_id; renderQueue(jobs); showDetail(j.job_id); };
    const left = el("div");
    left.appendChild(el("div", "fname", j.original_name || j.job_id));
    const meta = (j.result && j.result.processing_metadata) ? `${j.result.processing_metadata.provider_detected}` : "";
    left.appendChild(el("div", "fmeta", `${meta || j.status}`));
    const right = el("div");
    const pill = el("span", "pill " + j.status, j.status);
    right.appendChild(pill);
    
    // Mostrar owner del job
    const jobOwner = (j.result && j.result.processing_metadata && j.result.processing_metadata.operator_id) 
      ? j.result.processing_metadata.operator_id 
      : null;
    if (jobOwner) {
      right.appendChild(el("span", "job-owner", `Owner: ${jobOwner}`));
    }
    
    // Botón reintentar: solo si es failed/needs_new_photo Y (es admin/reviewer O es owner)
    const canRetry = (j.status === "failed" || j.status === "needs_new_photo") && 
      (operatorConfig && (operatorConfig.role === "admin" || operatorConfig.role === "reviewer" || 
       (operatorConfig.role === "operator" && jobOwner === operatorConfig.id)));
    
    if (canRetry) {
      const rb = el("button", "btn retry", "Reintentar");
      rb.onclick = async (e) => { e.stopPropagation(); await jpost(api + "/jobs/" + j.job_id + "/retry"); refresh(); };
      right.appendChild(rb);
    }
    it.appendChild(left);
    it.appendChild(right);
    if (selectedJob === j.job_id) it.classList.add("active");
    q.appendChild(it);
  }
}

// ---- detalle ----
async function showDetail(jobId) {
  const d = $("#detail");
  try {
    const j = await jget(api + "/jobs/" + jobId);
    if (j.status === "ready") renderReady(j);
    else if (j.status === "confirmed") renderReady(j);
    else if (j.status === "failed") d.innerHTML = `<div class="error-box">Error: ${fmt(j.error)}</div>`;
    else if (j.status === "needs_new_photo") renderNeedsNewPhoto(j);
    else d.innerHTML = `<div class="empty">Estado: ${j.status}...</div>`;
  } catch (e) {
    d.innerHTML = '<div class="error-box">No se pudo cargar el detalle.</div>';
  }
}
function renderNeedsNewPhoto(j) {
  const d = $("#detail");
  const res = j.result || {};
  const qg = (res.processing_metadata || {}).quality_gate || {};
  const reasons = qg.reasons || [];
  let html = `<div class="cardhead"><h2>${fmt(j.original_name)}</h2><span class="pill needs_new_photo">nueva foto requerida</span></div>`;
  html += `<div class="error-box">La foto no pasó el control de calidad. Motivos:`;
  html += `<ul>${reasons.map((r) => `<li>${fmt(r.message)}</li>`).join("")}</ul></div>`;
  html += `<div class="actions"><button class="btn retry" id="retry-quality-btn">Reintentar</button></div>`;
  d.innerHTML = html;
  const rb = $("#retry-quality-btn");
  if (rb) rb.onclick = async () => { await jpost(api + "/jobs/" + j.job_id + "/retry"); refresh(); showDetail(j.job_id); };
}

async function renderReady(j) {
  const d = $("#detail");
  const res = j.result || {};
  const pm = res.processing_metadata || {};
  const so = res.structured_output || {};
  const validated = so.validated_fields || {};
  const rejected = so.rejected_fields || {};
  const missing = so.missing_fields || {};
  const candidates = so.candidate_fields || {};
  const fieldConfidence = so.field_confidence || {};
  const scores = res.field_scores || {};
  const fieldReport = res.field_report || {};
  const confirmed = j.confirmed;

  // Obtener labels de campos desde service schema
  const provider = pm.provider_detected || validated.provider || validated.service || "GAS";
  const labels = await getFieldLabels(provider);

  // Construir lista de campos esperados (orden: required fields primero, luego opcionales)
  const allFieldNames = [...new Set([...Object.keys(validated), ...Object.keys(rejected), ...Object.keys(missing), ...Object.keys(candidates)])];
  // Filtrar campos internos
  const fieldNames = allFieldNames.filter(f => !["provider", "service"].includes(f));

  let html = `<div class="cardhead"><h2>${fmt(j.original_name)}</h2><span class="pill ${j.status}">${j.status}</span></div>`;

  // Aviso de calidad
  const qg = pm.quality_gate || {};
  if (qg.verdict === "warn") {
    const reasons = qg.reasons || [];
    html += `<div class="warn-box">Aviso de calidad: posible baja confianza en los resultados.`;
    html += `<ul>${reasons.map((r) => `<li>${fmt(r.message)}</li>`).join("")}</ul></div>`;
  }

  // Imagen del documento
  html += `<div class="image-viewer">
    <img id="doc-image" src="${api}/jobs/${j.job_id}/image" alt="Documento" loading="lazy"/>
    <div class="image-toolbar">
      <button class="btn ghost" id="zoom-in" aria-label="Acercar">+</button>
      <button class="btn ghost" id="zoom-out" aria-label="Alejar">-</button>
      <button class="btn ghost" id="zoom-reset" aria-label="Restablecer zoom">R</button>
    </div>
  </div>`;

  // Texto OCR bruto
  if (res.raw_ocr_text) {
    html += `<details class="ocr-text-panel"><summary>Texto OCR bruto</summary><div class="terminal">${fmt(res.raw_ocr_text).replace(/</g, "<")}</div></details>`;
  }

  // Resumen contadores
  const summaryCounts = fieldReport.summary_counts || { accepted_count: 0, rejected_count: 0, missing_count: 0 };
  html += `<div class="summary">`;
  html += `<span class="sbadge ok">Aceptados: ${summaryCounts.accepted_count || 0}</span>`;
  html += `<span class="sbadge bad">Rechazados: ${summaryCounts.rejected_count || 0}</span>`;
  html += `<span class="sbadge miss">Faltantes: ${summaryCounts.missing_count || 0}</span>`;
  html += `<span class="sbadge">Proveedor: ${fmt(pm.provider_detected)} (${fmt(pm.provider_confidence)})</span></div>`;

  // Tabla de campos
  html += `<div class="fields-table-container"><table class="fields-table" role="grid" aria-label="Campos extraídos">`;
  html += `<thead><tr>
    <th scope="col">Campo</th>
    <th scope="col">Candidato (OCR)</th>
    <th scope="col">Valor validado (editable)</th>
    <th scope="col">Decisión automática</th>
    <th scope="col">Acción operador</th>
    <th scope="col">Motivo (req. si != confirmado)</th>
    <th scope="col">Scores</th>
  </tr></thead><tbody>`;

  for (const f of fieldNames) {
    const label = labels[f] || f;
    const candidateVal = candidates[f] ?? "";
    const validatedVal = validated[f] ?? "";
    const rejectedInfo = rejected[f] || null;
    const isMissing = f in missing;
    const confidence = fieldConfidence[f] || {};
    const decision = confidence.decision || (isMissing ? "missing" : "unknown");
    const ocrScore = confidence.ocr_score ?? scores[f] ?? 0;
    const extractionScore = confidence.extraction_score ?? 0;
    const finalScore = confidence.final_score ?? 0;

    // Determinar valor inicial para el input editable
    let initialValue = validatedVal;
    if (rejectedInfo) initialValue = rejectedInfo.value;
    else if (candidateVal) initialValue = candidateVal;

    // Determinar acción por defecto según decisión automática
    let defaultAction = "confirmed";
    if (decision === "needs_review") defaultAction = "corrected";
    else if (decision === "blocked" || decision === "missing") defaultAction = "unresolved";

    // Motivo prellenado desde rejected_fields.reason
    const prefillReason = rejectedInfo ? rejectedInfo.reason : "";

    const decisionBadge = getDecisionBadge(decision);
    const scoresHtml = `<span class="score-badge" title="OCR: ${ocrScore}, Extracción: ${extractionScore}, Final: ${finalScore}">${finalScore.toFixed(2)}</span>`;

    html += `<tr class="field-row" data-field="${f}">
      <td class="field-label"><label for="val-${f}">${label}</label></td>
      <td class="field-candidate">${fmt(candidateVal) || '<span class="empty-val">-</span>'}</td>
      <td class="field-value"><input type="text" id="val-${f}" data-field="${f}" value="${fmt(initialValue).replace(/"/g, &quot;)}" ${confirmed ? "disabled" : ""} aria-label="Valor para ${label}"/></td>
      <td class="field-decision">${decisionBadge}</td>
      <td class="field-action">
        <select class="state-sel" data-field="${f}" data-decision="${decision}" ${confirmed ? "disabled" : ""} aria-label="Acción para ${label}">
          <option value="confirmed" ${defaultAction === "confirmed" ? "selected" : ""}>Confirmado</option>
          <option value="corrected" ${defaultAction === "corrected" ? "selected" : ""}>Corregido</option>
          <option value="unresolved" ${defaultAction === "unresolved" ? "selected" : ""}>Sin resolver</option>
        </select>
      </td>
      <td class="field-reason">
        <input type="text" class="reason-input" data-field="${f}" value="${fmt(prefillReason).replace(/\"/g, '"')}" placeholder="Motivo..." ${confirmed ? "disabled" : ""} aria-label="Motivo para ${label}" ${defaultAction === "confirmed" ? "" : "required"}/>
      </td>
      <td class="field-scores">${scoresHtml}</td>
    </tr>`;
  }
  html += `</tbody></table></div>`;

  // Acciones
  html += `<div class="actions">`;
  if (!confirmed) html += `<button class="btn ok" id="confirm-btn" disabled>Confirmar revisión</button>`;
  html += `<a class="btn primary" id="dl-original" href="${api}/jobs/${j.job_id}/original">Ver JSON original</a>`;
  if (confirmed) html += `<a class="btn primary" id="dl-final" href="${api}/jobs/${j.job_id}/download">Descargar JSON final</a>`;
  html += `</div>`;

  d.innerHTML = html;

  if (!confirmed) {
    setupFieldValidation(j.job_id);
    setupImageViewer();
  }
}

function getDecisionBadge(decision) {
  const badges = {
    auto_accepted: '<span class="decision-badge auto">Auto-aceptado</span>',
    needs_review: '<span class="decision-badge review">Requiere revisión</span>',
    blocked: '<span class="decision-badge blocked">Bloqueado</span>',
    missing: '<span class="decision-badge missing">No encontrado</span>',
    unknown: '<span class="decision-badge unknown">-</span>',
  };
  return badges[decision] || badges.unknown;
}

async function getFieldLabels(provider) {
  if (fieldLabelsCache[provider]) return fieldLabelsCache[provider];
  try {
    const svc = await jget(`${api}/services/${provider}`);
    const labels = {};
    if (svc.fields) {
      for (const [fname, fdef] of Object.entries(svc.fields)) {
        labels[fname] = fdef.label || fname;
      }
    }
    fieldLabelsCache[provider] = labels;
    return labels;
  } catch (e) {
    return {};
  }
}

function setupFieldValidation(jobId) {
  const reasonInputs = document.querySelectorAll('.reason-input');
  const actionSelects = document.querySelectorAll('.state-sel');
  const confirmBtn = $("#confirm-btn");

  function validateAll() {
    let allValid = true;
    actionSelects.forEach(sel => {
      const field = sel.getAttribute("data-field");
      const action = sel.value;
      const reasonInput = document.querySelector(`.reason-input[data-field="${field}"]`);
      if (action !== "confirmed") {
        if (!reasonInput || !reasonInput.value.trim()) {
          allValid = false;
          if (reasonInput) reasonInput.classList.add("invalid");
        } else {
          if (reasonInput) reasonInput.classList.remove("invalid");
        }
      } else {
        if (reasonInput) reasonInput.classList.remove("invalid");
      }
    });
    confirmBtn.disabled = !allValid;
  }

  actionSelects.forEach(sel => {
    sel.addEventListener("change", () => {
      const field = sel.getAttribute("data-field");
      const reasonInput = document.querySelector(`.reason-input[data-field="${field}"]`);
      if (sel.value !== "confirmed") {
        reasonInput.required = true;
        reasonInput.style.opacity = "1";
      } else {
        reasonInput.required = false;
        reasonInput.style.opacity = "0.5";
      }
      validateAll();
    });
  });

  reasonInputs.forEach(inp => {
    inp.addEventListener("input", validateAll);
  });

  // Validación inicial
  validateAll();

  confirmBtn.onclick = () => confirmJob(jobId);
}

function setupImageViewer() {
  const img = $("#doc-image");
  const zoomIn = $("#zoom-in");
  const zoomOut = $("#zoom-out");
  const zoomReset = $("#zoom-reset");
  if (!img) return;

  let scale = 1;
  let translateX = 0;
  let translateY = 0;
  let isDragging = false;
  let startX, startY;

  function applyTransform() {
    img.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
  }

  zoomIn.onclick = () => { scale = Math.min(scale * 1.2, 5); applyTransform(); };
  zoomOut.onclick = () => { scale = Math.max(scale / 1.2, 0.3); applyTransform(); };
  zoomReset.onclick = () => { scale = 1; translateX = 0; translateY = 0; applyTransform(); };

  // Pan con mouse/touch
  const viewer = img.parentElement;
  viewer.addEventListener("mousedown", (e) => {
    if (e.target === img) {
      isDragging = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
      viewer.style.cursor = "grabbing";
    }
  });
  window.addEventListener("mousemove", (e) => {
    if (isDragging) {
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      applyTransform();
    }
  });
  window.addEventListener("mouseup", () => { isDragging = false; viewer.style.cursor = "grab"; });

  // Touch support
  viewer.addEventListener("touchstart", (e) => {
    if (e.target === img && e.touches.length === 1) {
      isDragging = true;
      startX = e.touches[0].clientX - translateX;
      startY = e.touches[0].clientY - translateY;
    }
  }, { passive: true });
  viewer.addEventListener("touchmove", (e) => {
    if (isDragging && e.touches.length === 1) {
      translateX = e.touches[0].clientX - startX;
      translateY = e.touches[0].clientY - startY;
      applyTransform();
    }
  }, { passive: true });
  viewer.addEventListener("touchend", () => { isDragging = false; });

  // Wheel zoom
  viewer.addEventListener("wheel", (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      scale = Math.min(Math.max(scale * delta, 0.3), 5);
      applyTransform();
    }
  }, { passive: false });

  viewer.style.cursor = "grab";
}

async function confirmJob(jobId) {
  const inputs = document.querySelectorAll('.field-value input[data-field]');
  const sels = document.querySelectorAll('.state-sel[data-field]');
  const reasonInputs = document.querySelectorAll('.reason-input[data-field]');
  const corrections = [];

  inputs.forEach((inp) => {
    const f = inp.getAttribute("data-field");
    const sel = document.querySelector(`.state-sel[data-field="${f}"]`);
    const reasonInput = document.querySelector(`.reason-input[data-field="${f}"]`);
    const state = sel ? sel.value : "confirmed";
    const reason = reasonInput ? reasonInput.value.trim() : "";
    corrections.push({ field: f, state, final_value: inp.value, reason: reason || undefined });
  });

  try {
    const res = await jpost(api + "/jobs/" + jobId + "/confirm", { confirmed_fields: corrections });
    $("#detail").insertAdjacentHTML("afterbegin", `<div class="sbadge ok">Confirmado: ${res.summary.confirmed_count} · corregidos: ${res.summary.corrected_count} · sin resolver: ${res.summary.unresolved_count}</div>`);
    refresh();
    showDetail(jobId);
  } catch (e) {
    alert("Error al confirmar: " + e.message);
  }
}

// ---- SSE ----
function connectSSE() {
  try {
    sse = new EventSource(api + "/stream");
    sse.onopen = () => { $("#conn-status").textContent = "conectado"; };
    sse.onmessage = (ev) => {
      try { const d = JSON.parse(ev.data); if (d.job_id && d.status) refresh(); } catch (_) {}
    };
    sse.onerror = () => { $("#conn-status").textContent = "reconectando..."; setTimeout(connectSSE, 3000); sse.close(); };
  } catch (e) { setTimeout(connectSSE, 3000); }
}

$("#export-link").onclick = (e) => { e.preventDefault(); window.open(api + "/export", "_blank"); };

// Inicialización: cargar config de operador y mostrar modal si falta
if (!loadOperatorConfig()) {
  showOperatorModal();
}
setupOperatorModal();
updateOperatorBadge();

refresh();
connectSSE();
setInterval(refresh, 4000);