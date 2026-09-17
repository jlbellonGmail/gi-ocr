# Adopción del circuito en un proyecto existente

## Para qué sirve

Esta guía es para cuando querés traer el circuito agéntico de este
template (analista → auditor → implementador → QA → code reviewer) a un
proyecto que **ya existe**, con su propio código, su propia
documentación y su propio pipeline de CI — en vez de arrancar un
repositorio vacío desde el template.

Mezclar dos repositorios así casi siempre genera colisiones de nombre:
carpetas o archivos que el template espera con un nombre exacto
(`runs/`, `AGENTS.md`, `ci.yml`, etc.) y que tu proyecto puede ya tener
usados para otra cosa. Esta guía te dice, elemento por elemento, qué
colisión es probable y cómo resolverla sin perder nada del proyecto
destino.

## Cuándo consultarla

Antes de copiar cualquier archivo del template sobre tu proyecto, y de
nuevo durante el proceso si te aparece una duda puntual sobre un archivo
concreto (por ejemplo, "¿qué hago si ya tengo un `ci.yml`?"). No hace
falta leerla de punta a punta de una sola vez: podés ir directo a la
sección del elemento que te está generando dudas.

## Cómo recorrer el checklist

El checklist completo, con el detalle técnico de cada colisión y su
estrategia de resolución, vive en
[`docs/tecnica/adopcion-proyecto-existente.md`](../tecnica/adopcion-proyecto-existente.md).
Recorrelo en este orden, que es el orden en que normalmente aparecen las
decisiones al adoptar el circuito:

1. **`.agentic/`** — la fuente canónica de roles, modelos y adaptadores.
   Si nunca adoptaste el circuito antes en este proyecto, se copia entero
   sin drama. Si ya lo habías adoptado antes (aunque sea parcialmente),
   hay que fusionar a mano antes de sobrescribir.
2. **`scripts/`** — los 11 scripts que hacen andar el circuito
   (`ready-for-pr.ps1`, `start-work-unit.ps1`, etc.). Se agregan junto a
   los scripts que ya tenga tu proyecto; solo hay que resolver si alguno
   coincide de nombre por casualidad.
3. **`runs/`** — la carpeta donde el circuito guarda spec, plan, tasks y
   demás artefactos de cada feature. Si tu proyecto ya usa `runs/` para
   otra cosa (por ejemplo, salidas de benchmarks), hay que mover ese
   contenido a otro nombre, porque `runs/` está fijo en el código del
   circuito.
4. **`docs/tecnica/` y `docs/usuario/`** — se fusionan con tu
   documentación existente, sin pisar nada; solo se agregan los archivos
   propios del template (`index.md`, `arquitectura.md`,
   `circuito-agentico.md`).
5. **`AGENTS.md`** — el archivo de instrucciones que leen los agentes IA.
   Si tu proyecto ya tiene uno, no se reemplaza entero: se fusiona
   sección por sección, conservando lo que es específico de tu proyecto
   (stack, estructura del repo) y trayendo tal cual las secciones que son
   del circuito en sí.
6. **Los 4 workflows de `.github/workflows/`**
   (`ci.yml`, `docs.yml`, `post-hitl-merge-gate.yml`,
   `post-merge-close-feature.yml`) — cada uno tiene su propia sección con
   el caso de colisión más probable (CI propio, generador de docs propio,
   nombre de archivo ya usado) y qué hacer en cada caso.

Cada sección de la guía técnica te dice explícitamente si la resolución
es "esto se puede automatizar sin pensar mucho" (por ejemplo, copiar
`.agentic/` si no había nada antes) o "esto es una decisión de tu equipo
que no se puede resolver en automático" (por ejemplo, qué generador de
sitio de documentación te quedás si ya tenías uno).

## Cómo correr opcionalmente el script de detección

Antes de tocar nada en el proyecto destino, podés correr
`scripts/check-adoption-conflicts.ps1` desde el checkout de este template
contra la carpeta del proyecto destino, para ver de antemano qué rutas
del template ya existen ahí:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check-adoption-conflicts.ps1 -TargetPath "C:\ruta\al\proyecto-destino"
```

Si no pasás `-TargetPath`, el script analiza el directorio actual desde
el que lo invocás.

El script imprime un reporte agrupado por elemento del checklist (igual
agrupamiento que la guía técnica), indicando qué rutas conocidas existen
y cuáles no. Al terminar:

- **Código de salida `0`**: ninguna ruta conocida del template existe
  todavía en el destino. Podés copiar el elemento correspondiente sin
  preocuparte por colisiones de nombre (aunque igual conviene revisar la
  guía técnica antes, por si el destino tiene algo con el mismo
  propósito pero otro nombre).
- **Código de salida distinto de cero (`1`)**: al menos una ruta conocida
  del template ya existe en el destino. Revisá el reporte para saber
  exactamente cuál, y andá a la sección correspondiente de
  [`docs/tecnica/adopcion-proyecto-existente.md`](../tecnica/adopcion-proyecto-existente.md)
  para resolver esa colisión puntual.
- **Si la ruta destino no existe o no es un directorio**, el script
  termina con un mensaje de error explícito y código de salida distinto
  de cero — no te va a decir "sin colisiones" por una ruta mal escrita.

Importante: el script **no resuelve nada por vos**. Solo te dice qué ya
existe. No compara si el contenido es igual o distinto al del template,
no mira el historial de git, y no copia ni fusiona ningún archivo. La
decisión de cómo resolver cada colisión reportada la tomás vos siguiendo
la guía técnica. Ver la sección "Límites de
`scripts/check-adoption-conflicts.ps1`" en la guía técnica para el
detalle completo de qué no hace el script.
