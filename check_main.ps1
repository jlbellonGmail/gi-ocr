. .\scripts\feature-contract.ps1
$s = Get-FeatureContractStatus -Slug '10-consola-revision-humana-profesional' -Title 'Consola de Revision Humana Profesional'
$s.Problems