"""Brique IA : génère la synthèse décisionnelle à partir des KPIs calculés par le pipeline.

Le modèle (Claude, API Anthropic) reçoit uniquement docs/kpis.json et une consigne stricte :
ne citer que des chiffres présents dans les données, signaler les hypothèses simulées
et conclure par une recommandation Go / No-Go argumentée.

Prérequis : pip install anthropic, et la variable d'environnement ANTHROPIC_API_KEY.
Commande : python -m src.ai_synthesis   (écrit docs/synthese_ia.md)
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

PROMPT = """Tu es analyste data pour le Comex de L'Oréal. Rédige en français une synthèse décisionnelle
sur le test d'ouverture de boutiques L'Oréal en propre en Allemagne, à partir de ces KPIs (JSON) :

{kpis}

Règles :
- N'utilise que des chiffres présents dans le JSON. N'invente aucune donnée.
- Les montants du business case reposent sur une base interne simulée et des hypothèses : dis-le.
- Structure : 1) Verdict en une phrase (Go, Go conditionnel ou No-Go). 2) Trois à cinq constats chiffrés,
  un par axe (marché, prix et marges, réseau, logistique, assortiment). 3) Risques principaux.
  4) Conditions de succès et prochaines étapes.
- Style : phrases courtes, lisibles par un dirigeant en deux minutes, sans jargon.
"""


def main():
    import anthropic  # importé ici pour que le reste du projet tourne sans la librairie

    kpis = json.loads((ROOT / "docs" / "kpis.json").read_text(encoding="utf-8"))
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": PROMPT.format(kpis=json.dumps(kpis, ensure_ascii=False, indent=2))}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text")
    out = ROOT / "docs" / "synthese_ia.md"
    out.write_text(f"# Synthèse IA\n\n_Générée par {MODEL} à partir de docs/kpis.json._\n\n{text}\n", encoding="utf-8")
    print(f"Écrit : {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
