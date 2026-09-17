# Routing dinámico

Para resolver una tarea por capacidades:

```powershell
pwsh -File .\scripts\resolve-agentic-model.ps1 -Role builder `
  -Capabilities coding,tools,debugging -SddLevel STANDARD `
  -Feature 13-routing-dinamico -Version v2.0.0
```

El router comprueba disponibilidad real mediante variables externas, respeta
el perfil de seguridad, usa fallback sólo si está autorizado y deja la razón
en `runs/v2.0.0/13-routing-dinamico/model-routing.jsonl`. Para pruebas
determinísticas puede usarse `-AllowMissingCredentials`.
