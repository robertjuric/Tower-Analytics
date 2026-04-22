-- =========================
-- MAIN TABLE
-- =========================

CREATE TABLE IF NOT EXISTS battle_reports (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),

    report_hash TEXT UNIQUE,

    battle_date TIMESTAMP,
    game_time_seconds INT,
    real_time_seconds INT,
    tier INT,
    wave INT,
    killed_by TEXT,
    coins_earned NUMERIC(50, 5),
    coins_per_hour NUMERIC(50, 5),
    cells_earned NUMERIC(50, 5),
    cells_per_hour NUMERIC(50, 5),
    notes TEXT,
    
    raw JSONB
);

-- =========================
-- ECONOMY TABLE
-- =========================

CREATE TABLE IF NOT EXISTS battle_economy (
    report_id INT REFERENCES battle_reports(id) ON DELETE CASCADE,
    category TEXT NOT NULL,   -- 'coins' or 'currencies'
    metric TEXT NOT NULL,     -- normalized key name
    value NUMERIC(50, 5),

    PRIMARY KEY (report_id, category, metric)
);

-- =========================
-- BATTLE ATTACK (Offense)
-- =========================
CREATE TABLE IF NOT EXISTS battle_attack (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES battle_reports(id) ON DELETE CASCADE,

    category TEXT NOT NULL,   -- 'damage', 'hits', 'kills'
    metric TEXT NOT NULL,     -- 'death_wave', 'projectiles', etc.
    value NUMERIC(50, 5) NOT NULL,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (report_id, category, metric)
);

-- =========================
-- BATTLE DEFENSE (Survivability)
-- =========================
CREATE TABLE IF NOT EXISTS battle_defense (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES battle_reports(id) ON DELETE CASCADE,

    category TEXT NOT NULL,   -- 'damage_taken', 'regen', 'block'
    metric TEXT NOT NULL,     -- 'tower', 'lifesteal', etc.
    value NUMERIC(50, 5) NOT NULL,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (report_id, category, metric)
);

-- =========================
-- BATTLE UTILITY (Mechanics)
-- =========================
CREATE TABLE IF NOT EXISTS battle_utility (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES battle_reports(id) ON DELETE CASCADE,

    category TEXT NOT NULL,   -- 'utility', 'counts', 'records'
    metric TEXT NOT NULL,     -- 'waves_skipped', 'death_defy', etc.
    value NUMERIC(50, 5) NOT NULL,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (report_id, category, metric)
);

-- =========================
-- TAGS SYSTEM
-- =========================

CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS battle_report_tags (
    report_id INT REFERENCES battle_reports(id) ON DELETE CASCADE,
    tag_id INT REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (report_id, tag_id)
);

-- =========================
-- TOURNAMENT VIEW
-- =========================

CREATE OR REPLACE VIEW vw_tournament_reports AS
SELECT br.*
FROM battle_reports br
WHERE EXISTS (
    SELECT 1
    FROM battle_report_tags brt
    JOIN tags t ON t.id = brt.tag_id
    WHERE brt.report_id = br.id
      AND t.name = 'tournament'
);

-- =========================
-- OPTIONAL: INDEXES (performance)
-- =========================

CREATE INDEX IF NOT EXISTS idx_battle_date
ON battle_reports(battle_date);

CREATE INDEX IF NOT EXISTS idx_report_hash
ON battle_reports(report_hash);

CREATE INDEX IF NOT EXISTS idx_battle_economy_metric
ON battle_economy(metric);

CREATE INDEX IF NOT EXISTS idx_tag_name
ON tags(name);

CREATE INDEX IF NOT EXISTS idx_attack_report_id
    ON battle_attack(report_id);

CREATE INDEX IF NOT EXISTS idx_attack_metric
    ON battle_attack(metric);

CREATE INDEX IF NOT EXISTS idx_attack_category_metric
    ON battle_attack(category, metric);

CREATE INDEX IF NOT EXISTS idx_defense_report_id
    ON battle_defense(report_id);

CREATE INDEX IF NOT EXISTS idx_defense_metric
    ON battle_defense(metric);

CREATE INDEX IF NOT EXISTS idx_defense_category_metric
    ON battle_defense(category, metric);

CREATE INDEX IF NOT EXISTS idx_utility_report_id
    ON battle_utility(report_id);

CREATE INDEX IF NOT EXISTS idx_utility_metric
    ON battle_utility(metric);

CREATE INDEX IF NOT EXISTS idx_utility_category_metric
    ON battle_utility(category, metric);

CREATE INDEX IF NOT EXISTS idx_brt_report_id
ON battle_report_tags(report_id);

CREATE INDEX IF NOT EXISTS idx_brt_tag_id
ON battle_report_tags(tag_id);