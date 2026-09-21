# Atlas FSBM — autre implémentation

Explorateur des publications scientifiques de la Faculté des Sciences Ben M'Sik : carte des thèmes, recherche par similarité, filtres par chercheur, année et thème, et fiches d'articles.

Cette réalisation reprend **le sujet et les données** du projet fourni, avec une implémentation originale : API HTTP standard Python, interface JavaScript sans framework, index TF-IDF + analyse sémantique latente (SVD), groupes MiniBatch K-Means. Les positions sur la carte représentent les **deux premières dimensions latentes** ; il s'agit d'une vue exploratoire, et la distance affichée ne doit pas être interprétée comme une mesure bibliométrique exacte. La recherche fonctionne hors ligne, sans clé API. Elle est lexicale avec projection latente et ne remplace pas un modèle de phrases multilingue.

## Démarrer

```bash
python -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Ouvrir http://127.0.0.1:8000. Le premier démarrage construit l'index en mémoire. `python server.py --port 8080 --data chemin/vers/fsbm_dataset.json` permet de choisir le port et le fichier.

## Notebook de démonstration

```bash
pip install -r requirements-notebook.txt
jupyter lab notebooks/demo.ipynb
```

Le notebook `notebooks/demo.ipynb` fonctionne également dans Jupyter Notebook ou VS Code. Il suit six étapes comme le notebook de référence : inspection des données collectées, contrôle et dédoublonnage, vectorisation TF-IDF/SVD, recherches d’articles et de chercheurs, cartographie thématique, puis bilan. Les 16 cellules de code ont été vérifiées. Aucune nouvelle collecte ou clé API n’est nécessaire. Sélectionner l'environnement Python où les dépendances ont été installées, puis exécuter les cellules dans l'ordre.

## Structure

- `engine.py` : extraction, dédoublonnage, vectorisation, groupes, recherche.
- `server.py` : routes HTTP et distribution de l'interface.
- `web/` : page, styles et interactions de la carte.
- `notebooks/demo.ipynb` : exploration reproductible et visualisation des données.
- `data/fsbm_dataset.json` : copie du jeu de données fourni dans l'archive d'origine.
- `tests/` : vérification du dédoublonnage et des filtres.

