# Supply chain y CI/CD

El template verifica automáticamente Actions fijadas, permisos explícitos y
dependencias reproducibles. `product-tests` sigue siendo un placeholder hasta
que un proyecto destino documente su stack.

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate-supply-chain.ps1
pytest -q tests/test_supply_chain_policy.py
```

No hay release automático en F12; las releases pertenecen a F15.
