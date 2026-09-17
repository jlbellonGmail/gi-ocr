# Evidencias adaptativas

`feature-contract.ps1` es la fuente ejecutable. Un run v2 adaptativo se identifica por `sdd.json`, cuya profundidad proviene de ASSESS/SDD y no se recalcula aquí.

LIGHT exige SUMMARY y review; STANDARD agrega spec, plan, QA y docs; FULL agrega tasks, decision y audit. `convergence.json`, cuando existe, es evidencia máquina. Sin `sdd.json`, se mantiene legacy. Los artefactos opcionales no se reemplazan por archivos vacíos.
