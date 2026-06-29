"""Offline tests for the parsing logic, using fixtures captured from the live
site (no network needed). Run: python test_parsers.py"""

import json

import gpw_benchmark as g

# --- Fixture 1: WIBID/WIBOR table (exact structure from /dane-opoznione) ---
RATES_HTML = """
<table>
<thead>
<tr><th></th><th colspan="5">WIBID&reg;</th><th colspan="6">WIBOR&reg;</th></tr>
<tr><td>Data/Termin</td><td>ON</td><td>1M</td><td>3M</td><td>6M</td><td>SW</td>
    <td>ON</td><td>1M</td><td>3M</td><td>6M</td><td>1Y</td><td>SW</td></tr>
</thead>
<tr><td>2026-06-25</td><td>3,53</td><td>3,58</td><td>3,65</td><td>3,71</td><td>3,61</td>
    <td>3,81</td><td>3,78</td><td>3,85</td><td>3,91</td><td>3,95</td><td>3,81</td></tr>
<tr><td>2026-06-24</td><td>3,49</td><td>3,58</td><td>3,64</td><td>3,71</td><td>3,61</td>
    <td>3,77</td><td>3,78</td><td>3,84</td><td>3,91</td><td>3,96</td><td>3,81</td></tr>
</table>
"""

# --- Fixture 2: index list fragment (real CDATA from tab=tbsp) ---
INDEX_HTML = """<response><html><![CDATA[
<div class="cardBox borderRed"><p style="margin-bottom:0px;">Dane op&oacute;&zacute;nione o 15 minut</p></div>
<div class="table-responsive"><table class="footable table table2"><thead><tr style="background:#fff;">
<th class="firstth"></th><th class="w80px left">Skr&oacute;t</th><th class="right">Liczba instrument&oacute;w</th>
<th class="right">Czas ost. pub.</th><th class="right">Kurs otw.</th><th class="right">Kurs min.</th>
<th class="right">Kurs maks.</th><th class="right">Wart. ost.</th><th class="right">Zmiana do odn. (w&nbsp;%)</th>
<th class="right">% otw. portfela</th></tr></thead>
<tr><td><a class="indexChart" href="javascript:void(0)" onclick="javascript:getChartModal('PL9999999474','CURR',495175)"><img/></a></td>
<td class="left"><a href="/karta-indeksu?isin=PL9999999474">TBSP.Index</a></td>
<td class="right">19</td><td class="right">17:20:00</td><td class="right">2&nbsp;265,43</td><td class="right">2&nbsp;265,43</td>
<td class="right">2&nbsp;267,42</td><td class="right">2&nbsp;267,42</td><td class="right">0,20</td><td class="right">0</td></tr>
<tr><td><a class="indexChart" href="javascript:void(0)" onclick="javascript:getChartModal('PL9999996652','CURR',495175)"><img/></a></td>
<td class="left"><a href="/karta-indeksu?isin=PL9999996652">GPWB-B1Y3Y</a></td>
<td class="right">5</td><td class="right">17:20:00</td><td class="right">1&nbsp;329,12</td><td class="right">1&nbsp;329,12</td>
<td class="right">1&nbsp;329,34</td><td class="right">1&nbsp;329,34</td><td class="right">0,09</td><td class="right">0</td></tr>
</table></div>
]]></html><error><![CDATA[ 0 ]]></error></response>"""

# --- Fixture 3: chart-json payload (real 14D response) ---
CHART_JSON = json.loads(
    '[{"mode":"14D","isin":"PL9999999474","from":"2026-06-14","to":"2026-06-28",'
    '"data":[{"t":1781474400,"o":2247.65,"c":2249.62,"h":2249.62,"l":2247.65},'
    '{"t":1782424800,"o":2265.43,"c":2267.42,"h":2267.42,"l":2265.43}]}]'
)


def test_rates():
    cols, rows = g.parse_rates(RATES_HTML)
    assert cols == [
        "Date",
        "WIBID_ON",
        "WIBID_1M",
        "WIBID_3M",
        "WIBID_6M",
        "WIBID_SW",
        "WIBOR_ON",
        "WIBOR_1M",
        "WIBOR_3M",
        "WIBOR_6M",
        "WIBOR_1Y",
        "WIBOR_SW",
    ], cols
    assert len(rows) == 2
    assert rows[0]["Date"] == "2026-06-25"
    assert rows[0]["WIBID_ON"] == 3.53
    assert rows[0]["WIBOR_SW"] == 3.81
    assert rows[1]["WIBID_ON"] == 3.49
    print("test_rates OK:", cols)


def test_indices():
    rows = g.parse_index_table(INDEX_HTML, "tbsp")
    assert len(rows) == 2, len(rows)
    r = rows[0]
    assert r["isin"] == "PL9999999474"
    assert r["shortcode"] == "TBSP.Index"
    assert r["cmng_id"] == "495175"
    assert r["num"] == 19
    assert r["last_time"] == "17:20:00"
    assert r["open"] == 2265.43
    assert r["max"] == 2267.42
    assert r["change_pct"] == 0.20
    assert rows[1]["isin"] == "PL9999996652"
    print("test_indices OK:", {k: r[k] for k in ("isin", "shortcode", "open", "change_pct")})


def test_series():
    import types

    class FakeResp:
        def __init__(self, payload):
            self._p = payload

        def json(self):
            return self._p

        @property
        def text(self):
            return json.dumps(self._p)

    client = types.SimpleNamespace(get=lambda url, params=None: FakeResp(CHART_JSON))
    rows = g.fetch_series(client, ["PL9999999474"], "14D")
    assert len(rows) == 2
    assert rows[0]["isin"] == "PL9999999474"
    assert rows[0]["open"] == 2247.65 and rows[0]["close"] == 2249.62
    assert rows[0]["high"] == 2249.62 and rows[0]["low"] == 2247.65
    # epoch -> Warsaw date
    assert rows[0]["date"] == "2026-06-15", rows[0]["date"]
    assert rows[1]["date"] == "2026-06-26", rows[1]["date"]
    print("test_series OK:", [r["date"] for r in rows])


def test_num():
    assert g._num("2 265,43") == 2265.43
    assert g._num("3,81") == 3.81
    assert g._num(" - ") is None
    assert g._num("") is None
    print("test_num OK")


if __name__ == "__main__":
    test_num()
    test_rates()
    test_indices()
    test_series()
    print("\nALL TESTS PASSED")
