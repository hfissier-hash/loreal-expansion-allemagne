"""Contrôles de l'entrepôt. Commande : python -m unittest discover tests (après src.build_warehouse)."""
import csv
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/warehouse/warehouse.sqlite"


class WarehouseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DB.exists():
            raise unittest.SkipTest("Lancer d'abord src.simulate_transactions puis src.build_warehouse")
        cls.db = sqlite3.connect(DB)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def one(self, sql):
        return self.db.execute(sql).fetchone()[0]

    def test_no_orphan_foreign_keys(self):
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_detail_matches_aggregated_revenue_per_store_and_brand(self):
        target = {}
        with open(ROOT / "data/raw/interne/boutiques_france.csv", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                target[r["store_id"], r["brand"]] = float(r["revenue_ttc_eur"])
        actual = dict(((s, b), v) for s, b, v in self.db.execute("""
            SELECT st.store_code, p.brand, SUM(f.revenue_ttc) FROM fact_sales f
            JOIN dim_store st USING (store_key) JOIN dim_product p USING (product_key) GROUP BY 1, 2"""))
        for key, value in target.items():
            self.assertLess(abs(actual[key] - value) / value, 0.005, key)

    def test_conversion_matches_store_rate(self):
        with open(ROOT / "data/raw/interne/boutiques_france.csv", encoding="utf-8") as f:
            rate = {r["store_id"]: float(r["diag_conversion_rate"]) for r in csv.DictReader(f)}
        for store, measured in self.db.execute("""SELECT st.store_code, AVG(converted) FROM fact_diagnostic
                                                  JOIN dim_store st USING (store_key) GROUP BY 1"""):
            self.assertAlmostEqual(measured, rate[store], delta=0.001)

    def test_revenue_arithmetic(self):
        self.assertEqual(self.one("""SELECT COUNT(*) FROM fact_sales
            WHERE ABS(revenue_ttc - quantity * unit_price_ttc) > 0.01
               OR ABS(gross_margin_ht - (revenue_ht - cogs_ht)) > 0.01"""), 0)

    def test_sales_after_diagnostic_point_to_converted_diagnostic(self):
        self.assertEqual(self.one("""SELECT COUNT(*) FROM fact_sales s LEFT JOIN fact_diagnostic d USING (diagnostic_id)
            WHERE s.sale_type = 'apres_diagnostic' AND COALESCE(d.converted, 0) = 0"""), 0)

    def test_target_cities(self):
        rows = {r[0] for r in self.db.execute("SELECT city_name FROM dim_city WHERE city_role = 'cible_2027'")}
        self.assertEqual(rows, {"München", "Düsseldorf", "Frankfurt am Main"})

    def test_rents_are_monthly(self):
        self.assertAlmostEqual(self.one("""SELECT rent_eur_m2_month FROM fact_rent JOIN dim_city USING (city_key)
            JOIN dim_location USING (location_key) WHERE city_name = 'Düsseldorf' AND location_code = 'artere_n1'"""), 285.0)  # BNP Paribas RE S1 2026

    def test_hub_distance_matches_gold_dim_ville(self):
        with open(ROOT / "data/gold/dim_ville.csv", encoding="utf-8") as f:
            gold = {r["city"]: float(r["distance_karlsruhe_km"]) for r in csv.DictReader(f)}
        for city, km in self.db.execute("""SELECT city_name, distance_km_route_estimee FROM fact_hub_distance
                JOIN dim_hub USING (hub_key) JOIN dim_city USING (city_key)
                WHERE hub_name = 'Karlsruhe' AND dim_city.country_code = 'DE'"""):
            self.assertAlmostEqual(km, gold[city], delta=1, msg=city)

    def test_business_case_complete(self):
        self.assertEqual(self.one("SELECT COUNT(*) FROM fact_business_case WHERE ebitda_eur IS NULL"), 0)
        self.assertEqual(self.one("SELECT COUNT(DISTINCT scenario_key) FROM fact_deployment_plan"), 3)

    def test_all_panel_indicators_loaded(self):
        with open(ROOT / "data/raw/externe/panels_marche.csv", encoding="utf-8") as f:
            expected = sum(1 for _ in csv.DictReader(f))
        self.assertEqual(self.one("SELECT COUNT(*) FROM fact_market_indicator"), expected)
        self.assertEqual(self.one("SELECT COUNT(*) FROM fact_market_indicator WHERE value IS NULL"), 0)

    def test_basket_matches_team_hypothesis(self):
        # hypothèse de l'équipe : ≈ 56 € TTC après diagnostic, ≈ 35 € sans diagnostic
        basket = dict(self.db.execute("""SELECT sale_type, AVG(ca) FROM
            (SELECT ticket_id, sale_type, SUM(revenue_ttc) AS ca FROM fact_sales GROUP BY 1, 2) GROUP BY 1"""))
        self.assertAlmostEqual(basket["apres_diagnostic"], 56, delta=2)
        self.assertAlmostEqual(basket["sans_diagnostic"], 35, delta=2)


if __name__ == "__main__":
    unittest.main()
