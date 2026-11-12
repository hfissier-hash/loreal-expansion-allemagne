# Synthèse IA

_Générée par Claude (Anthropic) à partir de `docs/kpis.json`, avec la consigne de `src/ai_synthesis.py`. Pour la régénérer après une mise à jour des données : `python -m src.ai_synthesis`._

_Chiffres mis à jour à la main le 12/11/2026 après l'intégration du relevé de prix dans le business case (indice 106,7 au lieu de 98,2) : à régénérer avec la commande ci-dessus dès qu'une clé API est disponible._

## Verdict

**Go conditionnel, limité à 3 boutiques pilotes en 2027** (München, Düsseldorf, Frankfurt am Main, en rue commerçante 1a). Les 3 pilotes remboursent leur investissement en 3,9 ans dans le scénario réaliste. **Pas d'engagement à 15 boutiques à ce stade** : dans les trois scénarios, le plan 3 → 8 → 15 n'est pas remboursé fin 2031.

## Constats

- **Marché** : l'Allemagne est le premier marché beauté d'Europe (18,0 Md€ en 2025, +6,3 %), et le soin de la peau y croît de +11,1 %. Mais un Allemand dépense 48 € par an en soins de la peau, contre 66 € pour un Français (−27 %). Le concept diagnostic de peau part donc d'une base plus petite qu'en France.
- **Prix et marges** : les soins du catalogue sont 6,7 % plus chers en Allemagne qu'au prix public conseillé français (indice 106,7, relevé de 8 soins pondéré par marque), et 17,9 % plus chers qu'aux prix remisés des pharmacies en ligne françaises. L'écart vient surtout de CeraVe et SkinCeuticals ; Lancôme est moins cher en Allemagne. La TVA à 19 % rend 0,8 % de CA hors taxe en plus à prix TTC égal. Le taux de marge brute de référence (70,3 %) est préservé.
- **Réseau** : une boutique pilote ferait environ 660 000 à 780 000 € de CA par an, pour 435 000 € d'investissement (aménagement, appareils de diagnostic, ouverture). En rue 1a, le loyer coûte 4 à 7 % du CA. Sur l'artère n°1, il en coûte 28 à 58 %, et aucune des 8 villes n'est rentable.
- **Logistique** : l'usine L'Oréal de Karlsruhe est en moyenne à 271 km des 3 villes pilotes, contre 708 km pour Rambouillet. Aucun droit de douane dans l'Union européenne.
- **Assortiment** : 94,6 % du catalogue soin français est éligible. Les marques dermatologiques (La Roche-Posay, CeraVe, Vichy) sont le cœur de l'offre.

## Chiffres clés du business case (scénario réaliste)

| | 2027 | 2028 | 2029 | 2030 | 2031 |
|---|---|---|---|---|---|
| Boutiques ouvertes | 3 | 8 | 15 | 15 | 15 |
| CA TTC | 1,49 M€ | 4,05 M€ | 8,11 M€ | 9,34 M€ | 9,80 M€ |
| EBITDA | 0,02 M€ | 0,13 M€ | 0,48 M€ | 1,08 M€ | 1,31 M€ |
| Trésorerie cumulée (après investissements) | −1,28 M€ | −3,33 M€ | −5,89 M€ | −4,81 M€ | −3,50 M€ |

Le plan devient rentable seulement si les boutiques font **22 % de CA de plus** que l'estimation réaliste (7 880 €/m²), soit environ **9 600 € par m² et par an**. C'est plus que les boutiques françaises de région (8 578 €/m²).

**Attention** : ces montants reposent sur une base interne simulée (20 boutiques France) et sur des hypothèses de coûts. Ils donnent un ordre de grandeur, pas un engagement.

## Risques

- La densité de vente des boutiques françaises est simulée : c'est le paramètre le plus sensible du modèle.
- La concurrence est forte et installée : les drogeries font 53 % des ventes de cosmétiques, dm détient à lui seul 46,8 % du marché des drogeries, et les pharmacies vendent déjà les marques dermatologiques.
- Une boutique en propre peut concurrencer les distributeurs partenaires de L'Oréal.

## Conditions de succès et prochaines étapes

1. Ouvrir 3 boutiques pilotes en 2027, en rue 1a uniquement, jamais en flagship.
2. Déclencher la vague 2028 seulement si les pilotes atteignent au moins 9 600 € de CA par m² sur 12 mois, avec un taux de conversion des diagnostics proche de celui de la France (60 %).
3. Remplacer la base simulée par les vrais chiffres des boutiques françaises, et refaire tourner le pipeline.
4. Étudier une alternative moins coûteuse : des corners diagnostic chez dm, Rossmann ou en pharmacie.
5. Étiquetage en allemand et enregistrement LUCID avant l'ouverture.
