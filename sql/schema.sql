-- Entrepôt du projet L'Oréal Allemagne : constellation de faits (dimensions partagées).
-- SQL standard : exécuté dans SQLite par src/build_warehouse.py, importable dans DrawSQL (PostgreSQL).
-- dim_* = dimensions, fact_* = faits, ref_* = référentiels hors étoile.
-- Clés de substitution entières (*_key) ; la clé 0 d'une dimension = « non renseigné ».

-- ================= DIMENSIONS =================

CREATE TABLE dim_date (
    date_key      INTEGER PRIMARY KEY,   -- AAAAMMJJ
    full_date     DATE    NOT NULL,
    year          INTEGER NOT NULL,
    quarter       INTEGER NOT NULL,
    month         INTEGER NOT NULL,
    month_name    TEXT    NOT NULL,
    iso_week      INTEGER NOT NULL,
    weekday       INTEGER NOT NULL,      -- 1 = lundi … 7 = dimanche
    weekday_name  TEXT    NOT NULL,
    is_weekend    INTEGER NOT NULL
);

CREATE TABLE dim_country (
    country_code               TEXT PRIMARY KEY,
    country_name               TEXT,
    vat_standard_pct           REAL,
    customs_duty_intra_eu_pct  REAL,
    price_level_index_eu100    REAL,
    pli_year                   INTEGER,
    source_ids                 TEXT
);

CREATE TABLE dim_city (
    city_key                        INTEGER PRIMARY KEY,
    city_name                       TEXT NOT NULL UNIQUE,
    region                          TEXT,
    country_code                    TEXT NOT NULL REFERENCES dim_country(country_code),
    city_role                       TEXT NOT NULL,   -- cible_2027 | comparaison_de | pilote_fr
    population                      INTEGER,
    population_year                 INTEGER,
    population_status               TEXT,
    purchasing_power_eur_per_capita REAL,
    purchasing_power_index          REAL,
    purchasing_power_year           INTEGER,
    lat                             REAL,
    lon                             REAL,
    source_ids                      TEXT
);

CREATE TABLE dim_location (
    location_key   INTEGER PRIMARY KEY,
    location_code  TEXT NOT NULL UNIQUE,   -- rue_1a | artere_n1
    location_name  TEXT NOT NULL
);

CREATE TABLE dim_scenario (
    scenario_key    INTEGER PRIMARY KEY,
    scenario_name   TEXT NOT NULL UNIQUE,  -- Pessimiste | Réaliste | Optimiste
    revenue_factor  REAL NOT NULL
);

CREATE TABLE dim_store (
    store_key     INTEGER PRIMARY KEY,
    store_code    TEXT NOT NULL UNIQUE,    -- FR001… (pilotes simulés), DE01… (projets 2027)
    store_name    TEXT NOT NULL,
    city_key      INTEGER NOT NULL REFERENCES dim_city(city_key),
    store_status  TEXT NOT NULL,           -- pilote_fr | projet_de
    surface_m2    REAL,
    opening_year  INTEGER,
    is_simulated  INTEGER NOT NULL
);

CREATE TABLE dim_category (
    category_key   INTEGER PRIMARY KEY,    -- 0 = Total marché
    category_name  TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_product (
    product_key        INTEGER PRIMARY KEY,
    sku                TEXT NOT NULL UNIQUE,
    brand              TEXT NOT NULL,
    category_key       INTEGER NOT NULL REFERENCES dim_category(category_key),
    skin_concern       TEXT,
    list_price_fr_ttc  REAL,
    eligible_de        INTEGER NOT NULL,   -- 0 = gamme réservée à la France
    is_simulated       INTEGER NOT NULL
);

CREATE TABLE dim_customer (
    customer_key          INTEGER PRIMARY KEY,   -- 0 = client de passage non identifié
    customer_code         TEXT NOT NULL UNIQUE,
    gender                TEXT,
    age_band              TEXT,
    skin_type             TEXT,
    home_store_key        INTEGER REFERENCES dim_store(store_key),
    first_visit_date_key  INTEGER REFERENCES dim_date(date_key),
    loyalty_member        INTEGER,
    returned_6m           INTEGER
);

CREATE TABLE dim_retailer (
    retailer_key    INTEGER PRIMARY KEY,
    retailer_name   TEXT NOT NULL UNIQUE,
    segment         TEXT,
    stores_de       INTEGER,
    revenue_bn_eur  REAL,
    revenue_scope   TEXT,
    source_ids      TEXT,
    status          TEXT
);

CREATE TABLE dim_hub (
    hub_key       INTEGER PRIMARY KEY,
    hub_name      TEXT NOT NULL,
    country_code  TEXT NOT NULL REFERENCES dim_country(country_code),
    hub_type      TEXT,
    lat           REAL,
    lon           REAL,
    source_ids    TEXT
);

CREATE TABLE dim_source (
    source_id    TEXT PRIMARY KEY,
    source_name  TEXT,
    publisher    TEXT,
    url          TEXT,
    source_type  TEXT,
    reliability  TEXT
);

-- ================= FAITS INTERNES (boutiques pilotes France, simulés) =================

-- Grain : un diagnostic de peau.
CREATE TABLE fact_diagnostic (
    diagnostic_id            INTEGER PRIMARY KEY,
    date_key                 INTEGER NOT NULL REFERENCES dim_date(date_key),
    store_key                INTEGER NOT NULL REFERENCES dim_store(store_key),
    customer_key             INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    skin_type_detected       TEXT,
    main_concern             TEXT,
    duration_min             INTEGER,
    nb_products_recommended  INTEGER,
    converted                INTEGER NOT NULL   -- 1 = achat le jour du diagnostic
);

-- Grain : une ligne de ticket.
CREATE TABLE fact_sales (
    sale_line_id     INTEGER PRIMARY KEY,
    ticket_id        INTEGER NOT NULL,
    date_key         INTEGER NOT NULL REFERENCES dim_date(date_key),
    store_key        INTEGER NOT NULL REFERENCES dim_store(store_key),
    customer_key     INTEGER NOT NULL REFERENCES dim_customer(customer_key),
    product_key      INTEGER NOT NULL REFERENCES dim_product(product_key),
    diagnostic_id    INTEGER REFERENCES fact_diagnostic(diagnostic_id),
    sale_type        TEXT NOT NULL,     -- apres_diagnostic | rachat | sans_diagnostic
    quantity         INTEGER NOT NULL,
    unit_price_ttc   REAL NOT NULL,
    revenue_ttc      REAL NOT NULL,
    revenue_ht       REAL NOT NULL,
    cogs_ht          REAL NOT NULL,
    gross_margin_ht  REAL NOT NULL
);

-- ================= FAITS EXTERNES (collectés) =================

-- Grain : pays × année × catégorie.
CREATE TABLE fact_market (
    country_code          TEXT    NOT NULL REFERENCES dim_country(country_code),
    year                  INTEGER NOT NULL,
    category_key          INTEGER NOT NULL REFERENCES dim_category(category_key),
    value_bn_eur          REAL,
    share_pct             REAL,
    growth_pct            REAL,
    spend_per_capita_eur  REAL,
    source_ids            TEXT,
    PRIMARY KEY (country_code, year, category_key)
);

-- Grain : pays × périmètre × acteur × année.
CREATE TABLE fact_market_share (
    country_code      TEXT    NOT NULL REFERENCES dim_country(country_code),
    scope             TEXT    NOT NULL,
    player            TEXT    NOT NULL,
    year              INTEGER NOT NULL,
    market_share_pct  REAL,
    source_ids        TEXT,
    status            TEXT,
    PRIMARY KEY (country_code, scope, player, year)
);

-- Grain : ville × enseigne.
CREATE TABLE fact_competition (
    city_key         INTEGER NOT NULL REFERENCES dim_city(city_key),
    retailer_key     INTEGER NOT NULL REFERENCES dim_retailer(retailer_key),
    store_count      INTEGER,
    stores_per_100k  REAL,
    source_ids       TEXT,
    status           TEXT,
    PRIMARY KEY (city_key, retailer_key)
);

-- Grain : ville × emplacement. Loyer ramené en €/m²/mois.
CREATE TABLE fact_rent (
    city_key           INTEGER NOT NULL REFERENCES dim_city(city_key),
    location_key       INTEGER NOT NULL REFERENCES dim_location(location_key),
    rent_eur_m2_month  REAL,
    rent_raw           REAL,
    unit_raw           TEXT,
    period             TEXT,
    trend_pct_pa       REAL,
    source_ids         TEXT,
    PRIMARY KEY (city_key, location_key)
);

-- Grain : produit relevé × pays × enseigne (relevé manuel, références nommées).
CREATE TABLE fact_price (
    product_name  TEXT NOT NULL,
    brand         TEXT NOT NULL,
    size          TEXT,
    country_code  TEXT NOT NULL REFERENCES dim_country(country_code),
    retailer      TEXT NOT NULL,
    price_ttc     REAL,
    price_ht      REAL,
    collected_at  DATE,
    status        TEXT,
    PRIMARY KEY (product_name, brand, country_code, retailer)
);

-- Grain : hub × ville.
CREATE TABLE fact_hub_distance (
    hub_key                    INTEGER NOT NULL REFERENCES dim_hub(hub_key),
    city_key                   INTEGER NOT NULL REFERENCES dim_city(city_key),
    distance_km_vol_oiseau     REAL NOT NULL,
    distance_km_route_estimee  REAL NOT NULL,   -- vol d'oiseau × facteur_route (hypotheses.csv)
    PRIMARY KEY (hub_key, city_key)
);

-- ================= FAITS DU BUSINESS CASE (calculés par src/build.py) =================

-- Grain : ville × emplacement × scénario (une boutique type, année pleine).
CREATE TABLE fact_business_case (
    city_key                   INTEGER NOT NULL REFERENCES dim_city(city_key),
    location_key               INTEGER NOT NULL REFERENCES dim_location(location_key),
    scenario_key               INTEGER NOT NULL REFERENCES dim_scenario(scenario_key),
    revenue_ttc_eur            REAL,
    revenue_ht_eur             REAL,
    gross_margin_eur           REAL,
    rent_eur                   REAL,
    staff_eur                  REAL,
    other_costs_eur            REAL,
    logistics_eur              REAL,
    ebitda_eur                 REAL,
    ebitda_margin_pct          REAL,
    capex_eur                  REAL,
    payback_years              REAL,
    breakeven_revenue_ttc_eur  REAL,
    PRIMARY KEY (city_key, location_key, scenario_key)
);

-- Grain : scénario × année du plan (date_key = 31/12 de l'année).
CREATE TABLE fact_deployment_plan (
    scenario_key         INTEGER NOT NULL REFERENCES dim_scenario(scenario_key),
    year                 INTEGER NOT NULL,
    date_key             INTEGER NOT NULL REFERENCES dim_date(date_key),
    stores               INTEGER,
    revenue_ttc_eur      REAL,
    ebitda_eur           REAL,
    capex_eur            REAL,
    cumulative_cash_eur  REAL,
    PRIMARY KEY (scenario_key, year)
);

-- ================= RÉFÉRENTIELS (hors étoile) =================

CREATE TABLE ref_hypotheses (
    parameter  TEXT PRIMARY KEY,
    value      REAL,
    unit       TEXT,
    rationale  TEXT
);

CREATE TABLE ref_reglementation (
    topic       TEXT PRIMARY KEY,
    france      TEXT,
    allemagne   TEXT,
    impact      TEXT,
    source_ids  TEXT
);
