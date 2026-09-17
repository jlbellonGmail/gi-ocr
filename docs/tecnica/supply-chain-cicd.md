# Supply chain y CI/CD

F12 endurece la automatización propia del template sin asumir un stack de
producto ni implementar releases (F15).

## Controles

- Las Actions externas están fijadas a SHA completo y conservan un comentario
  de versión para facilitar actualizaciones deliberadas.
- Cada workflow declara permisos; `write` queda limitado al job que realmente
  publica documentación o ejecuta el cierre autorizado. No se usa `write-all`.
- `requirements-dev.txt` y `requirements-docs.txt` fijan versiones exactas.
- `scripts/validate-supply-chain.ps1` comprueba SHAs, permisos, dependencias,
  retención de artifacts si aparecen y patrones evidentes de secretos.

## CI, artifacts y releases

CI mantiene separados circuito, producto (placeholder agnóstico) y
reconciliador Windows. No se agregan artifacts porque el template no produce
un build de producto propio. La futura F15 deberá construir desde un
commit/tag validado, conservar el SHA en la evidencia y ejecutar gates antes
de publicar; F12 no agrega workflow de release, deployment, SBOM ni
provenance incompletos.

## Node.js 20 y compatibilidad

La inspección no encontró `setup-node` ni una dependencia Node en el template.
Las advertencias reportadas no provienen de un workflow Node propio. Los
scripts siguen siendo PowerShell y los tests del reconciliador siguen en
Windows. El guard de `develop` conserva escritura porque revierte/restaura y
registra incidentes; el gate post-HITL conserva escritura porque puede
mergear la PR autorizada.
