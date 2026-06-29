# GPW Benchmark — endpoint reference

All endpoints were verified by inspecting the live gpwbenchmark.pl front end's
own network traffic (June 2026). No API key is required for this public data.
Polish UI is the default; most endpoints accept `lang=EN` or have an `/en-`
page variant.

The site is fronted by an F5/BIG-IP WAF. Blind parameter fuzzing gets you a
"Request Rejected" page. Stick to the exact request shapes below, send a normal
`User-Agent` and a `Referer`, and throttle.

---

## 1. WIBID / WIBOR delayed reference rates

**Page (server-rendered HTML — no AJAX):**

```
GET https://gpwbenchmark.pl/dane-opoznione        (PL)
GET https://gpwbenchmark.pl/en-dane-opoznione     (EN)
```

The table lives directly in the page HTML inside `<main>`. NOTE: a plain
"reader" extraction of the page can drop the table — fetch the raw HTML and
parse the `<table>` that contains both "WIBID" and "WIBOR".

Structure (two header rows):

| row | cells |
|-----|-------|
| group row | `(empty)`, `WIBID®` colspan=5, `WIBOR®` colspan=6 |
| tenor row | `Data/Termin`, then `ON 1M 3M 6M SW` (WIBID), then `ON 1M 3M 6M 1Y SW` (WIBOR) |
| data rows | `YYYY-MM-DD`, then numeric values, comma decimal e.g. `3,53` |

Coverage: **year-to-date**, one business-day delayed, updated daily ~23:00.
Tenor set can change over time (e.g. `SW` was added 22 Dec 2025), so derive
columns from the header rather than hard-coding them.

---

## 2. Index list (all categories, with ISINs)

```
GET https://gpwbenchmark.pl/ajaxindex.php
        ?action=GPWIndexes
        &start=showTable
        &tab=<TAB>
        &lang=PL
```

Response is XML: `<response><html><![CDATA[ <div>…<table>…</table> ]]></html>
<error><![CDATA[ 0 ]]></error></response>`. Pull the HTML out of the CDATA and
parse the table(s).

`<TAB>` values (match the section anchors on `/notowania`):

| tab | meaning |
|-----|---------|
| `indexes` | Indeksy główne (main) — incl. a real-time table + 15-min delayed table |
| `macroindices` | Makroindeksy |
| `indexes_other` | Indeksy pozostałe |
| `national` | Indeksy narodowe |
| `sectorbased` | Indeksy sektorowe |
| `indexes_strategy` | Indeksy strategii |
| `benchmarks` | Benchmarki |
| `tbsp` | Indeksy obligacji (bonds) |

Each row gives:
- ISIN — from the `href="/karta-indeksu?isin=PLxxxxxxxxxx"` link.
- Shortcode/name — the link text (e.g. `WIG20`, `TBSP.Index`).
- `cmng_id` — the 3rd arg of `getChartModal('ISIN','CURR',<cmng_id>)` (an internal id).
- Snapshot columns — vary by table; map them from each table's own `<thead>`
  labels: `Skrót, Liczba spółek/instrumentów, Czas ost. pub., TWI, Kurs otw.,
  Kurs min., Kurs maks., Wart. ost., Zmiana do odn. (w %), % otw. portfela,
  Wartość obrotu skum. (w tys. zł)`.

The same ISIN can appear in more than one tab — de-duplicate by ISIN.

---

## 3. Per-index historical OHLC time series

```
GET https://gpwbenchmark.pl/chart-json.php
        ?req=[{"isin":"PL9999999474","mode":"1R"}]
        &t=<unix_millis>
```

- `req` is a JSON **array** — you may request several `{isin, mode}` objects in
  one call (the script batches this).
- `t` is a cache-buster (current time in ms).
- `mode` ∈ `14D, 1M, 3M, 6M, 1R`. **`MAX` returns no data** — on the site MAX is
  just a client-side "zoom to all" over whatever was already loaded, not a
  server window. `1R` (one year) is the longest server-provided window.

Response:

```json
[{"mode":"1R","isin":"PL9999999474","from":"2025-06-28","to":"2026-06-28",
  "data":[{"t":1751234400,"o":2133.7,"c":2132.65,"h":2133.7,"l":2132.65}, …]}]
```

- `t` — epoch **seconds**. Convert in **Europe/Warsaw** time to get the correct
  trading date (UTC conversion can land on the previous calendar day).
- `o/h/l/c` — open / high / low / close index value.
- An unknown ISIN or `MAX` yields the request echoed back with no `data` key.

For history longer than one year, GPW Benchmark publishes downloadable files
under "Dane historyczne" (`/dane_historyczne`, `/roczne`) — out of scope here.
