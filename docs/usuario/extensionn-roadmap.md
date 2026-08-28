# Extension de Roadmap Profesional - guia de usuario

Esta pagina explica que cambia para quien dirige el proyecto gi-ocr.

## Para que sirve

La extension agrega al `ROADMAP.md` las proximas etapas necesarias para
convertir el MVP local en una herramienta profesional de captura,
revision, auditoria e integracion documental.

No cambia el comportamiento del sistema OCR. No agrega endpoints, UI ni
procesamiento nuevo. Solo deja el backlog listo para iniciar features
futuras de forma ordenada.

## Como se usa

Para iniciar una nueva etapa, elegir un item pendiente del `ROADMAP.md` y
arrancar el circuito normal de `AGENTS.md`.

Ejemplo:

```text
Iniciar circuito agentico para 05-correccion-orientacion-exif desde
ROADMAP.md. Actua como analyst-agent y crea
runs/05-correccion-orientacion-exif/spec.md siguiendo AGENTS.md.
```

Cada item nuevo debe implementarse en su propia rama
`feature/<NN>-<slug>` y worktree propio bajo `../worktrees/<NN>-<slug>/`.

## Prioridad recomendada

La primera feature nueva recomendada es `05-correccion-orientacion-exif`,
porque las fotos reales de celular pueden verse derechas en visores pero
llegar rotadas al OCR si no se aplica el tag EXIF Orientation.

Despues conviene avanzar con calidad de captura, preprocesamiento
documental, regresion OCR y revision humana antes de ampliar despliegue o
cloud.

## Vision v2 cloud

`26-version-cloud-multitenant` queda registrado como vision futura para un
servicio SaaS pago. No bloquea el MVP local y requiere decision comercial e
infraestructura antes de implementarse.
