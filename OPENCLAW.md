# OPENCLAW.md — GI-OCR Agent Entry Point

GI-OCR / TGI-OCR trabaja con instrucciones locales reutilizables para reducir prompts largos.

Orden de lectura recomendado:

1. AGENTS.md
2. .agents/skills/gi-ocr-delivery-governance/SKILL.md
3. Skill específica según tarea:
   - gi-ocr-feature-builder
   - gi-ocr-recovery
   - gi-ocr-evidence-inspector
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
