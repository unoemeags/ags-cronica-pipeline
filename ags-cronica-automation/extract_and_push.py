#!/usr/bin/env python3
import os, re, json, argparse, hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import feedparser

# Google Sheets
from google.oauth2 import service_account
from googleapiclient.discovery import build

DEFAULT_HEADERS = [
  "id","fecha_detectada","hora_detectada","fuente","titulo_original","link","tema_sugerido",
  "actor_sugerido","resumen_neutral","relevancia","publicar","tipo_contenido","hora_recomendada",
  "notas_editor","hash_dedupe"
]

def now_local_iso():
    # Deja el timestamp en ISO; la hoja puede formatear.
    return datetime.now().astimezone().isoformat(timespec="seconds")

def normalize_url(url: str) -> str:
    try:
        p = urlparse(url.strip())
        q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
        q.sort()
        return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), ""))
    except Exception:
        return url.strip()

def stable_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

def classify_simple(title: str, excerpt: str):
    text = f"{title} {excerpt}".lower()
    # Reglas simples (fallback). Lo fino lo puedes mover a GitHub rules luego.
    if any(k in text for k in ["homicidio","robo","detención","operativo","cateo","fiscalía","policía","accidente"]):
        return "seguridad", "media", "noticia rápida", "12:00"
    if any(k in text for k in ["uaa","universidad","escuela","docentes","estudiantes","sep"]):
        return "educacion", "media", "contexto", "08:00"
    if any(k in text for k in ["imss","issste","hospital","clínica","medicamentos","brote","salud"]):
        return "salud", "media", "servicio", "08:00"
    if any(k in text for k in ["festival","feria","teatro","concierto","exposición","cultura"]):
        return "cultura", "baja", "crónica local", "18:00"
    if any(k in text for k in ["gobierno","congreso","cabildo","presupuesto","decreto","iniciativa","secretaría"]):
        return "gobierno", "media", "contexto", "10:00"
    return "general", "baja", "noticia rápida", "10:00"

def load_sources(path="sources.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("max_per_source", 25), data.get("sources", [])

def extract_items(max_per_source, sources):
    items = []
    for s in sources:
        if (s.get("type","rss").lower() != "rss") or not s.get("url"):
            continue
        feed = feedparser.parse(s["url"])
        src = s.get("name","Desconocido")
        for e in feed.entries[:max_per_source]:
            title = (e.get("title") or "").strip()
            link = normalize_url(e.get("link") or "")
            if not title or not link:
                continue
            published = e.get("published","") or e.get("updated","")
            excerpt = re.sub(r"\s+"," ", (e.get("summary") or e.get("description") or "")).strip()
            h = stable_hash(link)
            items.append({
                "source": src,
                "title": title,
                "url": link,
                "published": published,
                "excerpt": excerpt[:600],
                "hash": h
            })
    # dedupe by hash
    seen = set()
    out = []
    for it in items:
        if it["hash"] in seen:
            continue
        seen.add(it["hash"])
        out.append(it)
    return out

def sheets_client(service_account_json_path: str):
    creds = service_account.Credentials.from_service_account_file(
        service_account_json_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)

def ensure_headers(svc, sheet_id, tab_name):
    # Writes headers to row 1 if empty
    rng = f"{tab_name}!1:1"
    res = svc.spreadsheets().values().get(spreadsheetId=sheet_id, range=rng).execute()
    vals = res.get("values", [])
    if not vals or not vals[0]:
        svc.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!A1",
            valueInputOption="RAW",
            body={"values":[DEFAULT_HEADERS]}
        ).execute()

def append_rows(svc, sheet_id, tab_name, rows):
    svc.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{tab_name}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows}
    ).execute()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window_hours", type=int, default=3)
    args = ap.parse_args()

    sheet_id = os.getenv("SHEET_ID","").strip()
    tab = os.getenv("SHEET_TAB","Mesa de redaccion - AGS").strip()
    sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON","").strip()

    if not sheet_id or not sa_path:
        raise SystemExit("Faltan SHEET_ID o GOOGLE_SERVICE_ACCOUNT_JSON")

    max_per_source, sources = load_sources()
    items = extract_items(max_per_source, sources)

    # Build rows for sheet
    ts = datetime.now().astimezone()
    fecha = ts.date().isoformat()
    hora = ts.strftime("%H:%M:%S")

    rows = []
    for idx, it in enumerate(items, 1):
        tema, relev, tipo, hora_rec = classify_simple(it["title"], it["excerpt"])
        rows.append([
            it["hash"], fecha, hora, it["source"], it["title"], it["url"],
            tema, "", it["excerpt"], relev, "", tipo, hora_rec, "", it["hash"]
        ])

    svc = sheets_client(sa_path)
    ensure_headers(svc, sheet_id, tab)
    if rows:
        append_rows(svc, sheet_id, tab, rows)
        print(f"OK: agregadas {len(rows)} filas")
    else:
        print("OK: sin filas nuevas")

if __name__ == "__main__":
    main()
