# OPENCLAW.md — GI-OCR Agent Entry Point

GI-OCR / TGI-OCR trabaja con instrucciones locales reutilizables para reducir prompts largos.

Orden de lectura recomendado:

1. AGENTS.md
2. .agents/skills/delivery-governance/SKILL.md
3. Skill específica según tarea:
   - feature-builder
   - recovery
   - evidence-inspector
4. Prompt local correspondiente en .agents/prompts/
5. Template liviano correspondiente en .specify/templates/

Reglas clave:

- Español.
- Spec-Driven Development.
- Una tarea por vez.
- Evidencia real de terminal.
- No tocar producto fuera de alcance.
- No push automático.
- No T3.1/T3.2 sin instrucción explícita.

<!-- BEGIN GI-OCR MANAGED BLOCK: OPENCLAW-BRIDGE -->
Este archivo es un puente local para agentes OpenClaw/OpenCLAW.

No reemplaza AGENTS.md.

Reglas:

1. Usar AGENTS.md como fuente principal.
2. Obedecer skills y prompts versionados en .agents/.
3. Usar .specify/templates/ como base SDD.
4. Registrar specs concretas en specs/ cuando la tarea lo requiera.
5. No crear estructura base dentro de una feature funcional.
6. Si falta algo critico, detener y reportar recovery.
<!-- END GI-OCR MANAGED BLOCK: OPENCLAW-BRIDGE -->
