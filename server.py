import json
import html
import struct
import psycopg
import gzip
from collections import OrderedDict
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
cache = OrderedDict()
CACHE_MAX_SIZE = 100

VALID_ENCODINGS = {"utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"}

@app.route("/")
def index():
    with open("templates/index.html") as f:
        template = f.read()
    return Response(template)
@app.route("/sets")
def sets():
    # Encoding handling
    encoding = request.args.get("encoding", "utf-8").lower()
    if encoding not in VALID_ENCODINGS:
        encoding = "utf-8"
    with open("templates/sets.html") as f:
        template = f.read()
    row_parts = []
    start_time = perf_counter()
    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("select id, name from lego_set order by id")
            for row in cur.fetchall():
                html_safe_id = html.escape(row[0])
                html_safe_name = html.escape(row[1])
                row_parts.append(
                    f'<tr><td><a href="/set?id={html_safe_id}">{html_safe_id}</a></td><td>{html_safe_name}</td></tr>\n'
                )
        print(f"Time to render all sets: {perf_counter() - start_time}")
    finally:
        conn.close()
    rows = "".join(row_parts)
    page_html = template.replace("{ROWS}", rows)
    if encoding != "utf-8":
        page_html = page_html.replace('<meta charset="UTF-8">', '')
    html_bytes = page_html.encode(encoding)
    compressed = gzip.compress(html_bytes)
    print("Compressed size:", len(compressed))
    print("Original size:", len(html_bytes))
    resp = Response(compressed, direct_passthrough=True)
    resp.headers["Content-Type"] = f"text/html; charset={encoding}"
    resp.headers["Content-Encoding"] = "gzip"
    resp.headers["Content-Length"] = str(len(compressed))
    resp.headers["Cache-Control"] = "max-age=60"
    return resp
@app.route("/set")
def legoSet():  # We don't want to call the function `set`, since that would hide the `set` data type.
    with open("templates/set.html") as f:
        template = f.read()
    return Response(template)
@app.route("/api/set")
def apiSet():
    set_id = request.args.get("id")
    if set_id in cache:
        cache.move_to_end(set_id)
        return Response(json.dumps(cache[set_id], indent=4), content_type="application/json")
    start = perf_counter()
    conn = psycopg.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM lego_set WHERE id = %s", (set_id,))
            set_row = cur.fetchone()
            cur.execute("SELECT brick_type_id, color_id, count FROM lego_inventory WHERE set_id = %s", (set_id,))
            inventory_rows = cur.fetchall()
    finally:
        conn.close()
    print(f"DB query: {perf_counter() - start:.4f}s")
    if not set_row:
        return Response("Set not found", status=404)
    result = {
        "id": set_row[0],
        "name": set_row[1],
        "inventory": [
            {"brick_type_id": row[0], "color_id": row[1], "count": row[2]}
            for row in inventory_rows
        ]
    }
    cache[set_id] = result
    if len(cache) > CACHE_MAX_SIZE:
        cache.popitem(last=False)
    return Response(json.dumps(result, indent=4), content_type="application/json")

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

    parts = []

    set_id_bytes = set_row[0].encode("utf-8")
    parts.append(struct.pack("I", len(set_id_bytes)))
    parts.append(set_id_bytes)

    name_bytes = set_row[1].encode("utf-8")
    parts.append(struct.pack("I", len(name_bytes)))
    parts.append(name_bytes)

    parts.append(struct.pack("I", len(inventory_rows)))

    for row in inventory_rows:
        brick_type_id_bytes = row[0].encode("utf-8")
        parts.append(struct.pack("I", len(brick_type_id_bytes)))
        parts.append(brick_type_id_bytes)
        parts.append(struct.pack("I", row[1]))
        parts.append(struct.pack("I", row[2]))

    data = b"".join(parts)
    
    return Response(data, content_type="application/octet-stream")
if __name__ == "__main__":
    app.run(port=5000, debug=True)
# Note: If you define new routes, they have to go above the call to `app.run`.