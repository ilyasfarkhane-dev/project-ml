"""Index local des publications FSBM : modèle TF-IDF et projection latente."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "fsbm_dataset.json"


def extract_records(path: Path = DATA) -> tuple[list[dict], list[dict]]:
    """Une publication peut appartenir à plusieurs chercheurs : dédoublonner par ID/DOI."""
    source = json.loads(path.read_text(encoding="utf-8"))
    researchers = []
    papers: dict[str, dict] = {}
    for person in source["chercheurs"]:
        rid = str(person.get("chercheur_id") or person.get("openalex_id") or "")
        researchers.append({
            "id": rid, "name": person.get("nom_complet") or "Inconnu",
            "department": person.get("departement") or "Non renseigné",
            "count": len(person.get("articles") or []),
        })
        for article in person.get("articles") or []:
            key = str(article.get("article_id") or article.get("doi") or "").lower()
            if not key:
                key = (str(article.get("titre") or "") + str(article.get("annee") or "")).lower()
            if not key.strip():
                continue
            if key not in papers:
                papers[key] = {
                    "id": key, "title": article.get("titre") or "Sans titre",
                    "year": article.get("annee"), "abstract": article.get("abstract_clean") or article.get("abstract") or "",
                    "keywords": [str(k) for k in (article.get("mots_cles") or []) if isinstance(k, str)],
                    "citations": article.get("citations") or 0,
                    "journal": article.get("journal") or "",
                    "url": article.get("url") or ("https://doi.org/" + article["doi"] if article.get("doi") else ""),
                    "authors": list(article.get("auteurs") or []),
                    "researchers": [],
                }
            paper = papers[key]
            if rid and rid not in paper["researchers"]:
                paper["researchers"].append(rid)
            if not paper["abstract"] and (article.get("abstract_clean") or article.get("abstract")):
                paper["abstract"] = article.get("abstract_clean") or article.get("abstract")
            paper["citations"] = max(paper["citations"], article.get("citations") or 0)
    return list(papers.values()), researchers


class Atlas:
    def __init__(self, path: Path = DATA):
        self.papers, self.researchers = extract_records(path)
        if len(self.papers) < 3:
            raise ValueError("Le jeu de données doit contenir au moins trois publications")
        texts = [" ".join([p["title"]] * 2 + [p["abstract"][:1800]] + p["keywords"][:12]) for p in self.papers]
        self.vectorizer = TfidfVectorizer(strip_accents="unicode", lowercase=True,
                                          stop_words="english", ngram_range=(1, 2),
                                          min_df=2 if len(texts) > 100 else 1,
                                          max_df=.85, max_features=18000, sublinear_tf=True)
        sparse = self.vectorizer.fit_transform(texts)
        dimensions = min(64, sparse.shape[0] - 1, sparse.shape[1] - 1)
        if dimensions >= 2:
            self.reducer = TruncatedSVD(n_components=dimensions, random_state=42)
            latent = self.reducer.fit_transform(sparse)
            self.vectors = normalize(latent)
        else:
            self.reducer = None
            self.vectors = normalize(sparse.toarray())
        clusters = min(9, max(2, len(self.papers) // 50))
        self.kmeans = MiniBatchKMeans(n_clusters=clusters, random_state=42,
                                      batch_size=min(512, len(self.papers)), n_init=3)
        labels = self.kmeans.fit_predict(self.vectors)
        # La même représentation sert au placement et à la recherche.
        coords = self.vectors[:, :2].copy()
        coords -= coords.mean(axis=0)
        coords /= np.maximum(coords.std(axis=0), 1e-8)
        keywords = self.vectorizer.get_feature_names_out()
        self.topics = []
        for cluster in range(clusters):
            indices = np.flatnonzero(labels == cluster)
            weights = np.asarray(sparse[indices].mean(axis=0)).ravel()
            words = [keywords[i] for i in weights.argsort()[::-1] if len(keywords[i]) > 3][:4]
            self.topics.append({"id": cluster, "name": " · ".join(words[:2]),
                                "terms": words, "count": len(indices)})
        self.points = [{"id": p["id"], "x": round(float(coords[i, 0]), 3),
                        "y": round(float(coords[i, 1]), 3), "cluster": int(labels[i]),
                        "year": p["year"], "title": p["title"], "researchers": p["researchers"]}
                       for i, p in enumerate(self.papers)]
        self.by_id = {p["id"]: p for p in self.papers}

    def search(self, query="", researcher="", year=None, cluster=None, limit=30):
        limit = min(max(int(limit), 1), 100)
        query = query.strip()[:240]
        if query:
            query_vector = self.vectorizer.transform([query])
            if self.reducer:
                query_latent = normalize(self.reducer.transform(query_vector))
                scores = cosine_similarity(query_latent, self.vectors).ravel()
            else:
                scores = cosine_similarity(query_vector, self.vectorizer.transform(
                    [" ".join([p["title"], p["abstract"]]) for p in self.papers])).ravel()
        else:
            scores = np.array([p["citations"] for p in self.papers], dtype=float)
        eligible = []
        for i, paper in enumerate(self.papers):
            point = self.points[i]
            if researcher and researcher not in paper["researchers"]:
                continue
            if year is not None and paper["year"] != year:
                continue
            if cluster is not None and point["cluster"] != cluster:
                continue
            if query and scores[i] <= 0:
                continue
            eligible.append(i)
        eligible.sort(key=lambda i: (-scores[i], -self.papers[i]["citations"], self.papers[i]["id"]))
        return {"total": len(eligible), "items": [dict(self.papers[i], cluster=self.points[i]["cluster"],
                    score=round(float(scores[i]), 4) if query else None) for i in eligible[:limit]]}

    def overview(self):
        years = Counter(p["year"] for p in self.papers if isinstance(p["year"], int))
        return {"papers": len(self.papers), "researchers": len(self.researchers),
                "topics": self.topics, "people": self.researchers,
                "years": sorted(({"year": k, "count": v} for k, v in years.items()), key=lambda x: x["year"])}
