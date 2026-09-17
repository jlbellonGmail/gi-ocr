# Usar SDD adaptativo

Primero ejecuta ASSESS y conserva su evidencia. Luego materializa el perfil:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\materialize-sdd.ps1 `
  -AssessmentPath runs\assess.jsonl `
  -Objective "Describir el objetivo de la unidad" `
  -OutputPath runs\sdd-profile.json `
  -EvidencePath runs\sdd-profile.jsonl
```

El resultado indica `LIGHT`, `STANDARD` o `FULL` y qué evidencia corresponde
producir. El script no autoriza merge ni permite omitir la PR, CI o la decisión
humana previstas por el circuito v1.
