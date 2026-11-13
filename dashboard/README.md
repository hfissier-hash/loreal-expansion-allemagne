# Dashboard

Emplacement du dashboard de restitution (Lili).

Données à utiliser :
- `docs/kpis.json` : tous les KPIs calculés par `python -m src.build`
- `data/gold/` : tables du modèle en étoile (villes, business case, plan de déploiement, concurrence par ville…)
- `data/warehouse/` : entrepôt détaillé, régénéré par `python -m src.build_warehouse`
- `data/raw/sources.csv` : liste des sources à citer en bas du dashboard

Une fois le dashboard terminé, ouvrir une pull request vers `develop`.
