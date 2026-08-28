document.addEventListener('DOMContentLoaded', () => {
  const BASE_URL = 'http://localhost:8000/api/v1';
  const input = document.getElementById('camara_nativa');
  const statusEl = document.getElementById('status-message');
  const serviceListEl = document.getElementById('service-list');
  const toggleBtn = document.getElementById('toggle-services');
  const serviceSection = document.getElementById('service-section');
  const addServiceBtn = document.getElementById('add-service');
  const newServiceInput = document.getElementById('new-service-name');
  const logContainer = document.getElementById('log-container');
  const processLogEl = document.getElementById('process-log');

  // Helper to show status
  const setStatus = (msg, type = 'info') => {
    statusEl.textContent = msg;
    statusEl.className = type === 'error' ? 'status error' : 'status';
  };

  // Helper to format and display process_log
  const displayProcessLog = (log) => {
    if (!log) return;
    const lines = [
      `🔄 Engine: ${log['🔄 Engine'] || log.engine_used || 'Desconocido'}`,
      `📂 Archivo: ${log['📂 Archivo'] || log.file_processed || '-'}`,
      `📊 Líneas leídas: ${log['📊 Líneas leídas'] ?? log.raw_lines_found ?? '-'}`,
      `⏱️ Tiempo: ${log['⏱️ Tiempo'] || log.execution_time_seconds || '-'}`,
      ``,
      `📋 OCR Leído:`,
      `${log['💾 OCR Leído Completo'] || 'Sin OCR'}`,
      ``,
      `✅ Valores Extraídos:`,
      ...(log['✅ Valores Extraídos'] ? Object.entries(log['✅ Valores Extraídos']).map(([k, v]) => `  ${k}: ${v || '(no encontrado)'}`) : ['(sin datos)'])
    ];
    processLogEl.textContent = lines.join('\n');
    logContainer.style.display = 'block';
  };

  // Load existing services and display
  const loadServices = async () => {
    try {
      const res = await fetch(`${BASE_URL}/services`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      serviceListEl.innerHTML = '';
      data.services.forEach(svc => {
        const li = document.createElement('li');
        li.textContent = svc;
        const delBtn = document.createElement('button');
        delBtn.textContent = 'Eliminar';
        delBtn.style.marginLeft = '8px';
        delBtn.onclick = () => deleteService(svc);
        li.appendChild(delBtn);
        serviceListEl.appendChild(li);
      });
    } catch (e) {
      console.error('Error loading services:', e);
      setStatus(`Error cargar servicios: ${e.message}`, 'error');
    }
  };

  // Add a new service
  const saveService = async (name) => {
    try {
      const payload = { name, options: {} };
      const res = await fetch(`${BASE_URL}/services`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStatus('Servicio creado');
      await loadServices();
    } catch (e) {
      console.error('Error adding service:', e);
      setStatus(`Error crear servicio: ${e.message}`, 'error');
    }
  };

  // Delete a service
  const deleteService = async (name) => {
    try {
      const res = await fetch(`${BASE_URL}/services/${encodeURIComponent(name)}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStatus('Servicio eliminado');
      await loadServices();
    } catch (e) {
      console.error('Error deleting service:', e);
      setStatus(`Error eliminar servicio: ${e.message}`, 'error');
    }
  };

  // Capture image upload
  input.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) {
      setStatus('No se seleccionó ningún archivo.');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);
    setStatus('Enviando imagen...');
    try {
      const res = await fetch(`${BASE_URL}/capture`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStatus('Archivo procesado.');
      console.log('Server response:', data);
      // Display process log
      if (data.process_log) {
        displayProcessLog(data.process_log);
      }
      // TODO: map extracted_data to UI inputs (Total, Vencimiento)
    } catch (err) {
      console.error('Upload error:', err);
      setStatus(`Error: ${err.message}`, 'error');
    }
  });

  // Toggle service management UI
  toggleBtn.addEventListener('click', () => {
    const visible = serviceSection.style.display !== 'none';
    serviceSection.style.display = visible ? 'none' : 'block';
    if (!visible) loadServices();
  });

  // Add service button handler
  addServiceBtn.addEventListener('click', () => {
    const name = newServiceInput.value.trim();
    if (!name) {
      setStatus('Ingrese un nombre de servicio.');
      return;
    }
    saveService(name);
    newServiceInput.value = '';
  });
});