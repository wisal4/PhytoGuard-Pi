# Comment contribuer à PhytoGuard-Pi

## Branches
- `main` : version stable uniquement, personne ne push directement ici
- `dev` : intégration commune entre tous les membres
- `feat/membre-A` : branche personnelle du membre A
- `feat/membre-B` : branche personnelle du membre B
- `feat/membre-C` : branche personnelle du membre C
- `feat/membre-D` : branche personnelle du membre D

## Workflow (comment travailler)
1. Travaille toujours sur ta branche `feat/membre-X`
2. Fais des commits réguliers avec des messages clairs
3. Quand ta tâche est finie, ouvre une Pull Request vers `dev`
4. Un autre membre doit valider avant de merger

## Convention des commits
feat:  nouvelle fonctionnalité
fix:   correction de bug
doc:   documentation
test:  ajout de tests

Exemples :
  feat: add Flask route /diagnose
  fix: correct CLAHE threshold
  doc: update README installation

## Ce qu'il ne faut jamais faire
- Push directement sur `main`
- Committer le dossier `venv/`
- Committer les fichiers `.tflite` ou `.db` (trop lourds)