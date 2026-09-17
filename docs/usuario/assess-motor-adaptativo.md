# Evaluar una unidad de trabajo

ASSESS permite observar qué profundidad de trabajo se recomienda para un
cambio antes de activar el circuito adaptativo futuro. La salida no aprueba
ni integra cambios.

Ejemplo:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\assess-work-unit.ps1 `
  -ChangedPath scripts\mi-cambio.ps1,docs\usuario\mi-cambio.md `
  -EvidencePath runs\mi-assess.jsonl
```

El comando imprime JSON y registra la misma evaluación en JSONL. Interpreta
`risk` como `LOW`, `MEDIUM` o `HIGH`, y `depth` como `LIGHT`, `STANDARD` o
`FULL`. Si no puede demostrar qué rutas evaluar, termina con error. La
recomendación no elimina los pasos v1 vigentes ni permite hacer merge: la PR y
la decisión humana siguen siendo obligatorias.
