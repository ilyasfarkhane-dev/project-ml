import json
import tempfile
import unittest
from pathlib import Path
from sys import path

path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Atlas, extract_records


class AtlasTests(unittest.TestCase):
    def test_unique_publications_and_researcher_filter(self):
        def article(identifier, title, year):
            return {"article_id": identifier, "titre": title, "annee": year,
                    "abstract": "Study of scientific data and models", "citations": 2}
        data = {"chercheurs": [
            {"chercheur_id": "A1", "nom_complet": "Alice", "articles": [article("W1", "Neural networks", 2022), article("W2", "Graph structures", 2023)]},
            {"chercheur_id": "A2", "nom_complet": "Bob", "articles": [article("W1", "Neural networks", 2022), article("W3", "Molecular analysis", 2021)]},
        ]}
        with tempfile.TemporaryDirectory() as folder:
            location = Path(folder) / "dataset.json"
            location.write_text(json.dumps(data), encoding="utf-8")
            papers, people = extract_records(location)
            self.assertEqual((len(papers), len(people)), (3, 2))
            self.assertEqual(next(p for p in papers if p["id"] == "w1")["researchers"], ["A1", "A2"])
            atlas = Atlas(location)
            self.assertEqual(atlas.search(researcher="A1")["total"], 2)
            self.assertEqual(atlas.search(year=2021)["total"], 1)
            self.assertEqual(atlas.search(researcher="A2", year=2023)["total"], 0)
            self.assertEqual(len(atlas.points), 3)


if __name__ == "__main__":
    unittest.main()
