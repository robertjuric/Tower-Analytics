import time
import os
import psycopg2
import hashlib
import json
import re
from datetime import datetime
from psycopg2.extras import Json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

print("INGEST SCRIPT STARTING...")

MULTIPLIERS = {
    "": 1,
    "K": 1e3,
    "M": 1e6,
    "B": 1e9,
    "T": 1e12,
    "q": 1e15,
    "Q": 1e18,
    "s": 1e21,
    "S": 1e24,
}

def extract_tags_from_filename(path):
    # Extract stuff inside [ ... ]
    match = re.search(r"\[(.*?)\]", path)
    if not match:
        return []

    tags = match.group(1).split(",")

    # Clean up whitespace + normalize
    return [t.strip().lower() for t in tags if t.strip()]

def get_or_create_tag(cur, name):
    cur.execute("""
        INSERT INTO tags (name)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING
        RETURNING id
    """, (name,))

    result = cur.fetchone()

    if result:
        return result[0]

    # already exists → fetch it
    cur.execute("SELECT id FROM tags WHERE name = %s", (name,))
    return cur.fetchone()[0]

def add_tag_to_report(cur, report_id, tag_name):
    tag_id = get_or_create_tag(cur, tag_name)

    cur.execute("""
        INSERT INTO battle_report_tags (report_id, tag_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (report_id, tag_id))

def compute_hash(data):
    normalized = json.dumps(data, sort_keys=True)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()

def parse_number(value):
    if not value:
        return None

    # remove $ if present
    value = value.replace("$", "")

    match = re.match(r"([\d.]+)([A-Za-z]*)", value)
    if not match:
        raise ValueError(f"Invalid number: {value}")

    number = float(match.group(1))
    suffix = match.group(2)

    multiplier = MULTIPLIERS.get(suffix, 1)

    result = number * multiplier

    # print(f"PARSE DEBUG: {value} → {result}")  # temp debug

    return result

def parse_duration(text):
    if not text:
        return None

    total_seconds = 0

    matches = re.findall(r"(\d+)([dhms])", text)

    for value, unit in matches:
        value = int(value)

        if unit == "d":
            total_seconds += value * 86400
        elif unit == "h":
            total_seconds += value * 3600
        elif unit == "m":
            total_seconds += value * 60
        elif unit == "s":
            total_seconds += value

    return total_seconds

def parse_report(text):
    lines = text.splitlines()
    data = {}
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Key-value line
        if "\t" in line:
            key, value = line.split("\t", 1)

            if current_section:
                data.setdefault(current_section, {})[key] = value
            else:
                data[key] = value

        # Section header (only AFTER we've seen root data)
        else:
            # If we haven't seen any key-value pairs yet, ignore header
            if not data:
                continue

            current_section = line

    return data

def normalize_economy(data):
    rows = []

    coins = data.get("Coins", {})
    currencies = data.get("Currencies", {})

    # Coins
    for key, value in coins.items():
        rows.append({
            "category": "coins",
            "metric": key.lower().replace(" ", "_").replace("/", "_"),
            "value": parse_number(value)
        })

    # Currencies
    for key, value in currencies.items():
        rows.append({
            "category": "currencies",
            "metric": key.lower().replace(" ", "_"),
            "value": parse_number(value)
        })

    return rows    

def normalize_attack(data):
    rows = []

    damage = data.get("Damage", {})
    enemies_hit_by = data.get("Enemies Hit By", {})
    enemies_destroyed_by = data.get("Enemies Destroyed By", {})

    # Damage
    for key, value in damage.items():
        rows.append({
            "category": "damage",
            "metric": key.lower().replace(" ", "_").replace("/", "_"),
            "value": parse_number(value)
        })

    # Enemies Hit By
    for key, value in enemies_hit_by.items():
        rows.append({
            "category": "enemies_hit_by",
            "metric": key.lower().replace(" ", "_"),
            "value": parse_number(value)
        })

    # Enemies Destroyed By
    for key, value in enemies_destroyed_by.items():
        rows.append({
            "category": "enemies_destroyed_by",
            "metric": key.lower().replace(" ", "_"),
            "value": parse_number(value)
        })

    return rows   

def normalize_defense(data):
    rows = []

    bonus_health = data.get("Bonus Health Gained", {})
    health_regen = data.get("Health Regenerated", {})
    damage_taken = data.get("Damage Taken", {})
    damage_blocked = data.get("Damage Blocked", {})

    # Bonus Health Gained
    for key, value in bonus_health.items():
        rows.append({
            "category": "bonus_health",
            "metric": key.lower().replace(" ", "_").replace("/", "_"),
            "value": parse_number(value)
        })

    # Health Regenerated
    for key, value in health_regen.items():
        rows.append({
            "category": "health_regen",
            "metric": key.lower().replace(" ", "_"),
            "value": parse_number(value)
        })

    # Damage Taken
    for key, value in damage_taken.items():
        rows.append({
            "category": "damage_taken",
            "metric": key.lower().replace(" ", "_"),
            "value": parse_number(value)
        })

    # Damage Blocked
    for key, value in damage_blocked.items():
        rows.append({
            "category": "damage_blocked",
            "metric": key.lower().replace(" ", "_"),
            "value": parse_number(value)
        })

    return rows   

def normalize_utility(data):
    rows = []

    utility = data.get("Utility", {})
    counts = data.get("Counts", {})
    records = data.get("Records", {})
    killed_effect = data.get("Killed With Effect Active", {})
    total_enemies = data.get("Total Enemies", {})

    # Utility
    for key, value in utility.items():
        rows.append({
            "category": "utility",
            "metric": key.lower().replace(" ", "_").replace("/", "_"),
            "value": parse_number(value)
        })

    # Counts
    for key, value in counts.items():
        rows.append({
            "category": "counts",
            "metric": key.lower().replace(" ", "_"),
            "value": parse_number(value)
        })
    # Records
    for key, value in records.items():
        rows.append({
            "category": "records",
            "metric": key.lower().replace(" ", "_").replace("/", "_"),
            "value": parse_number(value)
        })

    # Killed With Effect Active
    for key, value in killed_effect.items():
        rows.append({
            "category": "killed_effect",
            "metric": key.lower().replace(" ", "_"),
            "value": parse_number(value)
        })
    # Total Enemies
    for key, value in total_enemies.items():
        rows.append({
            "category": "total_enemies",
            "metric": key.lower().replace(" ", "_"),
            "value": parse_number(value)
        })

    return rows   

def normalize(data):
    try:
        return {
            "battle_date": datetime.strptime(data["Battle Date"], "%b %d, %Y %H:%M"),
            "game_time": parse_duration(data["Game Time"]),
            "real_time": parse_duration(data["Real Time"]),
            "tier": int(data["Tier"]),
            "wave": int(data["Wave"]),
            "killed_by": data.get("Killed By"),
            "coins_earned": parse_number(data["Coins Earned"]),
            "coins_per_hour": parse_number(data["Coins Per Hour"]),
            "cells_earned": parse_number(data["Cells Earned"]),
            "cells_per_hour": parse_number(data["Cells Per Hour"]),
        }
    except Exception as e:
        print("NORMALIZE ERROR:", e)
        print("DATA:", data)
        raise

def insert_report(text, path=None):
    conn = psycopg2.connect(
        dbname="towerdb",
        user="tower",
        password="towerpass",
        host="db"
    )

    cur = conn.cursor()

    try:
        # --- Parse + normalize ---
        data = parse_report(text)
        core = normalize(data)

        # --- Hash ---
        report_hash = compute_hash(data)

        print("Inserting report with hash:", report_hash)

        # --- Insert report ---
        cur.execute("""
            INSERT INTO battle_reports (
                report_hash,
                battle_date,
                game_time_seconds,
                real_time_seconds,
                tier,
                wave,
                killed_by,
                coins_earned,
                coins_per_hour,
                cells_earned,
                cells_per_hour,
                raw
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (report_hash) DO NOTHING
            RETURNING id
        """, (
            report_hash,
            core["battle_date"],
            core["game_time"],
            core["real_time"],
            core["tier"],
            core["wave"],
            core["killed_by"],
            core["coins_earned"],
            core["coins_per_hour"],
            core["cells_earned"],
            core["cells_per_hour"],
            Json(data)
        ))

        result = cur.fetchone()
        # --- Handle duplicate vs new ---
        if not result:
            print("Duplicate report, fetching existing ID")

            cur.execute(
                "SELECT id FROM battle_reports WHERE report_hash = %s",
                (report_hash,)
            )
            report_id = cur.fetchone()[0]
        else:
            report_id = result[0]
            print("Inserted new report:", report_id)

        # --- TAGGING ---
        print("Adding tags for report:", report_id)

        # --- AUTO TAGS ---
        add_tag_to_report(cur, report_id, f"tier{core['tier']}")

        # --- FILENAME TAGS ---
        if path:
            file_tags = extract_tags_from_filename(path)
            print("Filename tags:", file_tags)
        
            for tag in file_tags:
                add_tag_to_report(cur, report_id, tag)

        # --- INSERT ECONOMY Report ---
        economy_rows = normalize_economy(data)
        print("ECONOMY ROWS:", len(economy_rows))
        for row in economy_rows:
            cur.execute("""
                INSERT INTO battle_economy (report_id, category, metric, value)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                report_id,
                row["category"],
                row["metric"],
                row["value"]
            ))
        # --- INSERT ATTACK Report ---
        attack_rows = normalize_attack(data)
        print("ATTACK ROWS:", len(attack_rows))
        for row in attack_rows:
            cur.execute("""
                INSERT INTO battle_attack (report_id, category, metric, value)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                report_id,
                row["category"],
                row["metric"],
                row["value"]
            ))
        # --- INSERT DEFENSE Report ---
        defense_rows = normalize_defense(data)
        print("DEFENSE ROWS:", len(defense_rows))
        for row in defense_rows:
            cur.execute("""
                INSERT INTO battle_defense (report_id, category, metric, value)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                report_id,
                row["category"],
                row["metric"],
                row["value"]
            ))
        # --- INSERT UTILITY Report ---
        utility_rows = normalize_utility(data)
        print("UTILITY ROWS:", len(utility_rows))
        for row in utility_rows:
            cur.execute("""
                INSERT INTO battle_utility (report_id, category, metric, value)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                report_id,
                row["category"],
                row["metric"],
                row["value"]
            ))

        # --- Commit ---
        conn.commit()
        print("Insert + tags successful")

    except Exception as e:
        print("ERROR during insert:", e)
        conn.rollback()

    finally:
        cur.close()
        conn.close()


class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".txt"):
            # print(f"Processing {event.src_path}")
            with open(event.src_path) as f:
                insert_report(f.read())


if __name__ == "__main__":
    time.sleep(5)

    seen_hashes = set()

    print("Polling for reports...")

    while True:
        try:
            # Force refresh by re-reading directory metadata
            files = list(os.scandir("/app/reports"))

            for entry in files:
                if not entry.name.endswith(".txt"):
                    continue

                path = entry.path
                # print(f"Processing {path}")

                with open(path, "r") as file:
                    text = file.read()
                report_hash = compute_hash(parse_report(text))

                if report_hash in seen_hashes:
                    continue

                seen_hashes.add(report_hash)
                insert_report(text, path)

        except Exception as e:
            print("Error:", e)

        time.sleep(2)