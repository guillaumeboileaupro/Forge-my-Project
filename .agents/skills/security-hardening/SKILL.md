---
name: security-hardening
description: Durcir le generateur, les archives produites et leurs pipelines.
---

# Durcissement securite
1. Cartographier donnees non fiables, systemes touches et frontieres de confiance.
2. Verifier traversal de chemins, ZIP Slip, injection, XSS, CSRF en contexte local, fuite de secrets.
3. Exiger des workflows CI minimaux et epingles pour toute activation.
4. Ajouter tests de regression sur chaque probleme de securite corrige.
5. Journaliser les scans effectivement executes, garder tout scan absent en NON VERIFIE.
6. Bloquer les alertes critiques/hautes non resolues; documenter le risque residuel.
