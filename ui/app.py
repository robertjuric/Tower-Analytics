# ui/app.py
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
import psycopg2

app = FastAPI()
env = Environment(loader=FileSystemLoader("/app/templates"))
#templates = Jinja2Templates(directory="/app/templates")

def get_conn():
    return psycopg2.connect(
        host="db",
        database="towerdb",
        user="tower",
        password="towerpass"
    )

def format_number(n):
    if n is None:
        return "0"

    n = float(n)

    for unit in ["", "K", "M", "B", "T", "Q"]:
        if abs(n) < 1000:
            return f"{n:.2f}{unit}"
        n /= 1000

    return f"{n:.2f}Q"

@app.get("/")
def index():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            r.id,
            r.battle_date,
            r.tier,
            r.wave,
            r.coins_earned,
            r.coins_per_hour,
            e.value AS cells,
            r.notes,
            COALESCE(STRING_AGG(t.name, ', '), '') AS tags
        FROM battle_reports r
        LEFT JOIN battle_economy e
            ON r.id = e.report_id AND e.metric = 'cells_earned'
        LEFT JOIN battle_report_tags rt ON r.id = rt.report_id
        LEFT JOIN tags t ON rt.tag_id = t.id
        GROUP BY
            r.id,
            r.battle_date,
            r.tier,
            r.wave,
            r.coins_earned,
            r.coins_per_hour,
            e.value,
            r.notes
        ORDER BY r.battle_date DESC
        LIMIT 100;
    """)

    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    conn.close()

    for r in rows:
        r["coins_earned_fmt"] = format_number(r.get("coins_earned"))
        r["coins_per_hour_fmt"] = format_number(r.get("coins_per_hour"))
        r["cells_fmt"] = format_number(r.get("cells"))

    template = env.get_template("index.html")
    html = template.render(rows=rows)

    return HTMLResponse(content=html)


@app.post("/tag/add")
def add_tag(report_id: int = Form(...), tag: str = Form(...)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("INSERT INTO tags (name) VALUES (%s) ON CONFLICT DO NOTHING", (tag,))
    cur.execute("""
        INSERT INTO battle_report_tags (report_id, tag_id)
        SELECT %s, id FROM tags WHERE name = %s
        ON CONFLICT DO NOTHING
    """, (report_id, tag))

    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)


@app.post("/tag/remove")
def remove_tag(report_id: int = Form(...), tag: str = Form(...)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM battle_report_tags
        WHERE report_id = %s
          AND tag_id = (SELECT id FROM tags WHERE name = %s)
    """, (report_id, tag))

    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)


@app.post("/note/update")
def update_note(report_id: int = Form(...), note: str = Form(...)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE battle_reports
        SET notes = %s
        WHERE id = %s
    """, (note, report_id))

    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)