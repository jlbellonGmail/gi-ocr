# Releases y evolución

Para validar una release ejecuta desde `develop` limpio:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\release-readiness.ps1 -Version v2.0.0 -DryRun
```

El resultado exitoso es sólo una validación: no publica nada. Si faltan fases,
CI, integridad, coherencia de ramas o el tag ya existe, la operación se
rechaza. La publicación requiere una PR `develop` → `main`, merge humano,
comprobación del SHA final, tag SemVer inmutable y una release breve. Un
patch/hotfix parte del tag estable, se valida igual y luego se integra a
`develop`.
