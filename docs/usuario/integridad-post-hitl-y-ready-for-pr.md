# Integridad post-HITL y ready-for-pr

## Qué riesgo real evita

El circuito agéntico tiene un único punto de intervención humana: tu
aprobación de la PR en GitHub. Esta feature cierra tres formas en las que
esa garantía podía quedar debilitada sin que te dieras cuenta:

1. **Tu aprobación podía quedar "vieja" sin que nadie te avisara.** Si
   aprobabas una PR y después alguien (por ejemplo `builder-agent`,
   respondiendo a un checkpoint fallido) pusheaba un commit nuevo a esa
   misma rama, y la rama `develop` no tenía activada la protección
   "descartar aprobaciones al pushear" en GitHub, el código nuevo podía
   terminar mergeado sin que vos lo hubieras visto ni aprobado
   realmente. Ahora el gate que corre después de tu aprobación
   (`scripts/complete-approved-pr.ps1`) verifica explícitamente que tu
   aprobación más reciente sea sobre el commit que realmente está en la
   PR ahora mismo.
2. **`ready-for-pr.ps1` podía dejar el ROADMAP a medio marcar.** Si algo
   del contrato de la feature estaba incompleto (faltaba `decision.md`,
   una doc técnica, etc.), el script podía haber marcado `ROADMAP.md`
   como `[-] READY_FOR_PR` y creado un commit local ANTES de descubrir
   el problema. Ahora la validación completa corre antes de tocar
   `ROADMAP.md`: si algo falla, no queda ningún commit espurio que
   deshacer a mano.
3. **El cuerpo de la PR tenía referencias genéricas.** En vez de decir
   "revisá `audit-N.md`" (un literal que no apunta a ningún archivo
   real), ahora dice el nombre real del archivo aprobado, por ejemplo
   `audit-2.md`.

## Qué vas a ver si tu aprobación queda obsoleta

Si aprobás una PR y después se pushea un commit nuevo a esa misma rama
(por ejemplo porque el gate post-HITL había rechazado algo y
`builder-agent` lo corrigió), la próxima corrida de
`complete-approved-pr.ps1` (disparada automáticamente por
`post-hitl-merge-gate.yml`) va a:

- **no mergear la PR**;
- comentar en la PR (si corre en GitHub Actions) un mensaje explícito
  diciendo que tu aprobación quedó obsoleta tras un push posterior y que
  se necesita que vuelvas a aprobar sobre el commit vigente;
- dejar evidencia en `runs/<slug>/post-hitl-gate-N.md` con
  `status: rejected`.

**Qué tenés que hacer:** volver a revisar la PR (que ahora incluye el
código nuevo) y volver a apretar "Approve" en GitHub. Es el mismo botón
de siempre — no es un checkpoint nuevo ni un paso extra que no existiera
antes. No es algo que `builder-agent` tenga que corregir: tu aprobación
anterior simplemente ya no cubre el código actual de la PR.

Si tu organización quiere evitar depender de este mensaje, la
configuración recomendada en GitHub es activar "Require approval of the
most recent reviewable push" en la protección de la rama `develop`
(Settings → Branches). Esta feature funciona igual con o sin esa
configuración activada; es una capa de defensa adicional en el script
para el caso en que esa protección no esté activa.

## Qué NO cambió

- Seguís siendo el único punto de aprobación humana del circuito. Esto no
  agrega un segundo checkpoint: es la misma aprobación de siempre, que
  ahora se verifica contra el commit real en vez de solo contra el
  estado "aprobado/no aprobado".
- No hay comandos nuevos que tengas que aprender: `ready-for-pr.ps1` y
  `complete-approved-pr.ps1` se siguen invocando exactamente igual que
  antes.
- No hay stack, backend ni dependencia nueva: todo el cambio vive en los
  scripts del propio motor del circuito.
