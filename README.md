# AGS Cronica Automation (v0)

Este proyecto extrae notas desde fuentes RSS (nacionales y locales), clasifica por tema y actualiza una Google Sheet
(Mesa de redaccion - AGS) para que el editor decida manualmente si se publica.

## Flujo
1) Se ejecuta 3 veces al dia (cada 3 horas a partir de las 7:00 am): 7:00, 10:00, 13:00 (hora local Mexico).
2) Lee fuentes RSS definidas en `sources.json`.
3) Normaliza y deduplica por URL.
4) Clasifica tema/actor usando listas en `ags-cronica-newsroom` (tu repo de reglas) o usando listas locales (fallback).
5) Inserta/actualiza filas en Google Sheets:
   - publicar = vacio (tu decides si / no)
   - tipo_contenido sugerido
   - hora_recomendada sugerida

## Requisitos
- Python 3.10+
- Credenciales Google Sheets (service account) en un archivo JSON (no se sube a GitHub).
- (Opcional) OPENAI_API_KEY para generar resumen neutral; si no hay, usa excerpt del RSS.

## Archivos
- `extract_and_push.py`: script principal
- `sources.json`: lista de feeds RSS
- `sheet_schema.md`: columnas sugeridas en tu Sheet
- `.github/workflows/schedule.yml`: ejemplo para GitHub Actions (cron en UTC)

## Como correr local
1) `pip install -r requirements.txt`
2) Define variables de entorno:
   - GOOGLE_SERVICE_ACCOUNT_JSON=/ruta/cred.json
   - SHEET_ID=... (id de tu Google Sheet)
   - SHEET_TAB=Mesa (o el nombre de tu pestaña)
   - OPENAI_API_KEY=... (opcional)
3) `python extract_and_push.py --window_hours 3`

## Nota sobre horas
GitHub Actions usa UTC. Ajusta el cron segun tu zona horaria.
