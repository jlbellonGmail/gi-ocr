// Captura OCR Local — frontend SPA (sin frameworks, vanilla JS)
const $ = (s) => document.querySelector(s);
const api = "/api/v1";
let selectedJob = null;
let sse = null;

// ---- utilidades ----
const fmt = (s) => (s == null ? "" : String(s));
function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  return e;
}
async function jget(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error((await r.text()) || r.status);
  return r.json();
}
async function jpost(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
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
  msg.textContent = `Enviando ${fileList.length} archivo(s)…`;
  try {
    const r = await fetch(api + "/jobs", { method: "POST", body: fd });
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
    if (j.status === "failed") {
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
    else d.innerHTML = `<div class="empty">Estado: ${j.status}…</div>`;
  } catch (e) {
    d.innerHTML = '<div class="error-box">No se pudo cargar el detalle.</div>';
  }
}
function renderReady(j) {
  const d = $("#detail");
  const res = j.result || {};
  const pm = res.processing_metadata || {};
  const so = res.structured_output || {};
  const validated = so.validated_fields || {};
  const rejected = so.rejected_fields || {};
  const missing = so.missing_fields || {};
  const scores = res.field_scores || {};
  const fields = Object.keys({ ...validated, ...rejected, ...missing });
  const confirmed = j.confirmed;

  let html = `<div class="cardhead"><h2>${fmt(j.original_name)}</h2><span class="pill ${j.status}">${j.status}</span></div>`;
  html += `<div class="summary">`;
  html += `<span class="sbadge ok">Aceptados: ${res.field_report ? res.field_report.summary_counts.accepted_count : "-"}</span>`;
  html += `<span class="sbadge bad">Rechazados: ${res.field_report ? res.field_report.summary_counts.rejected_count : "-"}</span>`;
  html += `<span class="sbadge miss">Faltantes: ${res.field_report ? res.field_report.summary_counts.missing_count : "-"}</span>`;
  html += `<span class="sbadge">Proveedor: ${fmt(pm.provider_detected)} (${fmt(pm.provider_confidence)})</span></div>`;
  html += `<div class="dgrid"><div class="fields">`;
  for (const f of fields) {
    let tag = "accepted", val = validated[f] ?? "";
    if (rejected[f]) { tag = "rejected"; val = rejected[f].value; }
    else if (f in missing) { tag = "missing"; val = ""; }
    const sc = scores[f] != null ? `<span class="score">conf ${scores[f]}</span>` : "";
    html += `<div class="field"><div class="label"><span>${f}</span><span class="tag ${tag}">${tag}</span></div>`;
    html += `<input data-f="${f}" value="${fmt(val).replace(/"/g, "&quot;")}" ${confirmed ? "disabled" : ""}/>`;
    html += `<select class="state-sel" data-state="${f}" ${confirmed ? "disabled" : ""}>
      <option value="confirmed">confirmado</option>
      <option value="corrected">corregido</option>
      <option value="unresolved">sin resolver</option></select>`;
    html += `${sc}</div>`;
  }
  html += `</div><div class="preview">`;
  if (res.raw_ocr_text) {
    html += `<details><summary>Texto OCR</summary><div class="terminal">${(res.raw_ocr_text || "").replace(/</g, "&lt;")}</div></details>`;
  }
  html += `</div></div>`;
  html += `<div class="actions">`;
  if (!confirmed) html += `<button class="btn ok" id="confirm-btn">Confirmar revisión</button>`;
  html += `<a class="btn primary" id="dl-original" href="${api}/jobs/${j.job_id}/original">Ver JSON original</a>`;
  if (confirmed) html += `<a class="btn primary" id="dl-final" href="${api}/jobs/${j.job_id}/download">Descargar JSON final</a>`;
  html += `</div>`;
  d.innerHTML = html;
  if (!confirmed && $("#confirm-btn")) $("#confirm-btn").onclick = () => confirmJob(j.job_id);
}
async function confirmJob(jobId) {
  const inputs = document.querySelectorAll('.field input[data-f]');
  const sels = document.querySelectorAll('.field select[data-state]');
  const corrections = [];
  inputs.forEach((inp) => {
    const f = inp.getAttribute("data-f");
    const sel = document.querySelector(`select[data-state="${f}"]`);
    const state = sel ? sel.value : "confirmed";
    corrections.push({ field: f, state, final_value: inp.value });
  });
  try {
    const res = await jpost(api + "/jobs/" + jobId + "/confirm", { confirmed_fields: corrections });
    $("#detail").insertAdjacentHTML("afterbegin", `<div class="sbadge ok">Confirmado: ${res.summary.confirmed_count} · corregidos: ${res.summary.corrected_count}</div>`);
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
    sse.onerror = () => { $("#conn-status").textContent = "reconectando…"; setTimeout(connectSSE, 3000); sse.close(); };
  } catch (e) { setTimeout(connectSSE, 3000); }
}

$("#export-link").onclick = (e) => { e.preventDefault(); window.open(api + "/export", "_blank"); };

refresh();
connectSSE();
setInterval(refresh, 4000);