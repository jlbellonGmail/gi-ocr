# Seguridad profesional

La ejecución autónoma continúa para cambios locales y verificaciones normales.
Las acciones con impacto remoto, merge, datos sensibles, escritura externa o
carácter destructivo requieren un gate proporcional.

La política se valida con:

```powershell
pwsh -NoProfile -File .\scripts\security-policy.ps1
```

No agregues tokens a archivos del repositorio ni a evidencias. Para una acción
externa, declara el servidor, operación, alcance y resultado sin valores
secretos. Una autorización sólo sirve para la unidad, acción, rama y base que
indica.
