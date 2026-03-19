import json
import html
import psycopg
from flask import Flask, Response, request
from time import perf_counter

app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "port": 9876,
    "dbname": "lego-db",
    "user": "lego",
    "password": "bricks",
}


@app.route("/")
def index():
    template = open("templates/index.html").read()
    return Response(template)


@app.route("/sets")
def sets():
    template = open("templates/sets.html").read()
    rows = ""

    start_time = perf_counter()
    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("select id, name from lego_set order by id")
            for row in cur.fetchall():
                html_safe_id = html.escape(row[0])
                html_safe_name = html.escape(row[1])
                existing_rows = rows
                rows = existing_rows + f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td><td>{html_safe_name}</td></tr>\n'
        print(f"Time to render all sets: {perf_counter() - start_time}")
    finally:
        conn.close()

    page_html = template.replace("{ROWS}", rows)
    return Response(page_html, content_type="text/html")


@app.route("/set")
def legoSet():  # We don't want to call the function `set`, since that would hide the `set` data type.
    template = open("templates/set.html").read()
    return Response(template)


@app.route("/api/set")
def apiSet():
    set_id = request.args.get("id")

    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM lego_set WHERE id = %s", (set_id,))
            set_row = cur.fetchone()

            cur.execute("""
                SELECT brick_type_id, color_id, count
                FROM lego_inventory
                WHERE set_id = %s
            """, (set_id,))
            inventory_rows = cur.fetchall()
    finally:
        conn.close()

    if not set_row:
        return Response("Set not found", status=404)

    result = {
        "id": set_row[0],
        "name": set_row[1],
        "inventory": []
    }

    for row in inventory_rows:
        result["inventory"].append({
            "brick_type_id": row[0],
            "color_id": row[1],
            "count": row[2]
        })

    json_result = json.dumps(result, indent=4)
    return Response(json_result, content_type="application/json")


@app.route("/api/set_binary")
def apiSetBinary():
    set_id = request.args.get("id")

    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM lego_set WHERE id = %s", (set_id,))
            set_row = cur.fetchone()

            cur.execute("""
                SELECT brick_type_id, color_id, count
                FROM lego_inventory
                WHERE set_id = %s
            """, (set_id,))
            inventory_rows = cur.fetchall()
    finally:
        conn.close()

    if not set_row:
        return Response("Set not found", status=404)

    data = b""

    set_id_bytes = set_row[0].encode("utf-8")
    data += struct.pack("I", len(set_id_bytes))
    data += set_id_bytes

    name_bytes = set_row[1].encode("utf-8")
    data += struct.pack("I", len(name_bytes))
    data += name_bytes

    data += struct.pack("I", len(inventory_rows))

    for row in inventory_rows:
        brick_type_id_bytes = row[0].encode("utf-8")
        data += struct.pack("I", len(brick_type_id_bytes))
        data += brick_type_id_bytes
        data += struct.pack("I", row[1])
        data += struct.pack("I", row[2])

    return Response(data, content_type="application/octet-stream")
if __name__ == "__main__":
    app.run(port=5000, debug=True)

# Note: If you define new routes, they have to go above the call to `app.run`.
