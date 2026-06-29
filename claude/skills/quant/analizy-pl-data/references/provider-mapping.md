# Provider Mapping Reference

Complete mapping of TFI companies to analizy.pl umbrella fund codes for portfolio PDF downloads.

## Download URL Pattern

```
https://dokumenty.analizy.pl/pobierz/fi/{FUND_CODE}/SP/{DATE}
```

- `FUND_CODE`: Umbrella fund code (see table below)
- `SP`: "Skład Portfela" (Portfolio Composition)
- `DATE`: Quarter-end date (YYYY-MM-DD): 03-31, 06-30, 09-30, 12-31

## Complete Provider List (26 Providers)

### Major TFIs (Large Fund Families)

| Provider ID | TFI Company | Umbrella Code | Funds | Report Size | Notes |
|-------------|-------------|---------------|-------|-------------|-------|
| goldmansachs | Goldman Sachs TFI | ING02 | 35 | 5.2MB | All ING codes return same bulk report |
| pko | PKO TFI | PCS05 | 34 | 408KB | PKO Parasolowy FIO |
| pekao | Pekao TFI | PIO01 | 32 | 6.4MB | All PIO codes return same bulk report |
| santander | Santander TFI | ARK04 | 27 | 2.2MB | ARK13 (Credit Agricole) is separate |
| bnpparibas | BNP Paribas TFI | FOR08 | 19 | 9.6MB | All FOR codes return same bulk report |
| uniqa | UNIQA TFI | AXA05 | 18 | 954KB | Some global funds have smaller reports |

### Medium TFIs

| Provider ID | TFI Company | Umbrella Code | Funds | Report Size | Notes |
|-------------|-------------|---------------|-------|-------------|-------|
| quercus | QUERCUS TFI | QRS03 | 14 | 410KB | QRS33/34 return 404 |
| mtfi | mTFI | MBK02 | 13 | 1MB | SKR116-119 also work |
| skarbiec | Skarbiec TFI | SKR01 | 12 | - | SKARBIEC + BPS FIO subfunds |
| millennium | Millennium TFI | MIL04 | 12 | 726KB | All MIL codes return same report |
| superfund | SUPERFUND TFI | SUP12 | 12 | 470KB | All SUP codes return same report |
| amundi | Amundi Polska TFI | AMU05 | 11 | 83KB | All AMU codes return same report |
| velofunds | VeloFunds TFI | NOB08 | 10 | 295KB | All NOB codes return same report |

### Smaller TFIs

| Provider ID | TFI Company | Umbrella Code | Funds | Report Size | Notes |
|-------------|-------------|---------------|-------|-------------|-------|
| investor | Investors TFI | DWS02 | 9 | - | Formerly DWS |
| pzu | TFI PZU | PZU01 | 8 | - | PZU + inPZU subfunds |
| alior | Alior TFI | MON03 | 8 | 1MB | All MON codes return same report |
| agiofunds | AgioFunds TFI | AGF04 | 7 | 267KB | All AGF codes return same report |
| allianz | TFI Allianz Polska | ALL01 | 7 | - | Allianz FIO umbrella |
| ipopema | Ipopema TFI | IPO154 | 6 | - | IPO02 returns 404, using IPO154 |
| rockbridge | Rockbridge TFI | AIG02 | 5 | - | Rockbridge Neo umbrella |
| esaliens | Esaliens TFI | KAH02 | 5 | - | KAH01 returns 404, using KAH02 |
| generali | Generali Investments TFI | UNI02 | 15 | - | UNI01 returns 404 |
| vig | VIG / C-QUADRAT TFI | VIG01 | 4 | - | VIG SFIO |
| caspar | Caspar TFI | CAS15 | 4 | 765KB | All CAS codes return same report |
| templeton | Templeton Asset Management TFI | TEM01 | 3 | 494KB | Franklin Templeton FIO |
| eques | Eques Investment TFI | PLJ51 | 1 | 186KB | Only 1 fund |

## Working vs Non-Working Codes

### Codes Returning 404

Some codes that appear in fund_master.csv don't work for bulk downloads:
- `IPO02` → Use `IPO154` instead
- `KAH01` → Use `KAH02` instead
- `UNI01` → Use `UNI02` instead
- `QRS33`, `QRS34` → Use `QRS03`
- `MBK03` → Use `MBK02`

### Same Report, Multiple Codes

Many TFIs return the same bulk report regardless of which subfund code is used:
- All `ING*` codes → Same Goldman Sachs report
- All `PIO*` codes → Same Pekao report
- All `FOR*` codes → Same BNP Paribas report
- All `MIL*` codes → Same Millennium report

## Parser Status

| Provider | Parser Status | Type |
|----------|--------------|------|
| rockbridge | ✅ Working | Custom |
| pzu | ✅ Working | Custom |
| skarbiec | ✅ Working | Custom |
| allianz | ✅ Working | Custom |
| generali | ✅ Working | Custom |
| vig | ✅ Working | Custom |
| ipopema | ✅ Working | Custom |
| investor | ✅ Working | Custom |
| esaliens | ✅ Working | Custom |
| quercus | ✅ Working | IZFiA |
| velofunds | ✅ Working | IZFiA |
| millennium | ✅ Working | IZFiA |
| alior | ✅ Working | IZFiA |
| santander | ✅ Working | IZFiA |
| bnpparibas | ✅ Working | IZFiA |
| pko | ✅ Working | IZFiA |
| amundi | ✅ Working | IZFiA |
| mtfi | ✅ Working | IZFiA |
| pekao | ⚠️ Needs parser | Has data |
| goldmansachs | ❌ Image PDF | Needs OCR |
| uniqa | ❌ Text PDF | No tables |
| superfund | ❌ Text PDF | No tables |
| agiofunds | ❌ Text PDF | No tables |
| caspar | ❌ Text PDF | No tables |
| templeton | ❌ Text PDF | No tables |
| eques | ❌ Text PDF | 1 fund only |

## Usage Example

```python
import requests
from pathlib import Path

def download_portfolio_pdf(provider: str, code: str, date: str, output_dir: Path):
    """Download portfolio PDF for a provider."""
    url = f"https://dokumenty.analizy.pl/pobierz/fi/{code}/SP/{date}"
    response = requests.get(url, timeout=60)

    if response.status_code == 200:
        filename = f"PAR_{code}__SP__{date}.pdf"
        output_path = output_dir / provider / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        return output_path
    else:
        raise ValueError(f"Failed to download: {url} (status: {response.status_code})")

# Example usage
download_portfolio_pdf("rockbridge", "AIG02", "2025-09-30", Path("data/raw/fund_holdings"))
```

## Configuration File

Full mapping is stored in `config/provider_mapping.json` with schema:

```json
{
  "download_url_pattern": "https://dokumenty.analizy.pl/pobierz/fi/{FUND_CODE}/SP/{DATE}",
  "quarter_end_dates": ["03-31", "06-30", "09-30", "12-31"],
  "providers": [
    {
      "provider_id": "rockbridge",
      "tfi_company": "Rockbridge TFI",
      "umbrella_codes": ["AIG02"],
      "umbrella_names": ["Rockbridge Neo FIO"],
      "download_verified": true,
      "notes": "..."
    }
  ]
}
```

## Last Verified

All URLs tested: 2026-01-26
