#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "requests>=2.28",
# ]
# ///
"""
Ticker Registry - Security master and cross-source ticker mapping service.

Provides unified lookup for converting between different ticker formats
across data sources (Bloomberg, Yahoo, Stooq, FRED, NBP).

Usage:
    uv run ticker_registry.py lookup PLXTRDM00011
    uv run ticker_registry.py convert XTB.WA stooq
    uv run ticker_registry.py discover PLXTRDM00011 US0378331005
    uv run ticker_registry.py  # Run self-tests

Module usage:
    from ticker_registry import TickerRegistry, convert_ticker, isin_to_yahoo

    # Initialize registry
    registry = TickerRegistry()

    # Convert ISIN to Yahoo ticker
    yahoo_ticker = registry.isin_to_ticker('PLXTRDM00011', source='yahoo')  # 'XTB.WA'

    # Convert any ticker to another format
    stooq_ticker = registry.convert_ticker('PKO.WA', to_source='stooq')  # 'pko'

    # Auto-discover missing Yahoo tickers
    discovered = registry.discover_missing_yahoo_tickers(['PLXTRDM00011'])
"""

from typing import Optional, Dict, List, Literal
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import csv

# Type definitions
SourceType = Literal['bloomberg', 'yahoo', 'stooq', 'fred', 'nbp']
InstrumentType = Literal['equity', 'index', 'currency', 'bond', 'commodity', 'etf']


@dataclass
class Security:
    """Represents a security/instrument with all its identifiers and metadata."""
    uid: str = ""  # Universal ID - primary key (e.g., isin_PLXTRDM00011, idx_WIG20, fx_USDPLN)
    isin: Optional[str] = None
    name: str = ""
    instrument_type: InstrumentType = "equity"
    country: str = ""
    exchange: str = ""
    tickers: Dict[str, Optional[str]] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)
    last_updated: Optional[datetime] = None
    mapping_source: str = "unknown"

    @property
    def primary_key(self) -> str:
        """Return uid as primary key."""
        return self.uid

    def get_ticker(self, source: SourceType) -> Optional[str]:
        """Get ticker for specific source."""
        return self.tickers.get(source)

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export."""
        return {
            'uid': self.uid,
            'isin': self.isin or '',
            'name': self.name,
            'instrument_type': self.instrument_type,
            'country': self.country,
            'exchange': self.exchange,
            'ticker_bloomberg': self.tickers.get('bloomberg', ''),
            'ticker_yahoo': self.tickers.get('yahoo', ''),
            'ticker_stooq': self.tickers.get('stooq', ''),
            'ticker_fred': self.tickers.get('fred', ''),
            'sector': self.metadata.get('sector', ''),
            'currency': self.metadata.get('currency', ''),
            'mapping_source': self.mapping_source,
            'last_updated': self.last_updated.isoformat() if self.last_updated else ''
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Security':
        """Create Security from dictionary (CSV row)."""
        tickers = {}
        for source in ['bloomberg', 'yahoo', 'stooq', 'fred']:
            key = f'ticker_{source}'
            if d.get(key):
                tickers[source] = d[key]

        metadata = {}
        if d.get('sector'):
            metadata['sector'] = d['sector']
        if d.get('currency'):
            metadata['currency'] = d['currency']

        last_updated = None
        if d.get('last_updated'):
            try:
                last_updated = datetime.fromisoformat(d['last_updated'])
            except ValueError:
                pass

        return cls(
            uid=d.get('uid', ''),
            isin=d.get('isin') or None,
            name=d.get('name', ''),
            instrument_type=d.get('instrument_type', 'equity'),
            country=d.get('country', ''),
            exchange=d.get('exchange', ''),
            tickers=tickers,
            metadata=metadata,
            last_updated=last_updated,
            mapping_source=d.get('mapping_source', 'csv')
        )


class TickerRegistry:
    """
    Central registry for security master data and ticker mappings.

    Features:
    - Load from CSV security_master file
    - Auto-discover Yahoo tickers via ISIN lookup
    - Bidirectional lookup: ISIN -> ticker or ticker -> ISIN
    - Single CSV file as both master and cache
    """

    # CSV columns in order
    CSV_COLUMNS = [
        'uid', 'isin', 'name', 'instrument_type', 'country', 'exchange',
        'ticker_bloomberg', 'ticker_yahoo', 'ticker_stooq', 'ticker_fred',
        'sector', 'currency', 'mapping_source', 'last_updated'
    ]

    def __init__(
        self,
        csv_path: Optional[Path] = None,
        auto_discover: bool = True
    ):
        """
        Initialize registry.

        Args:
            csv_path: Path to security_master.csv (default: skill data directory)
            auto_discover: Whether to auto-lookup missing Yahoo tickers
        """
        if csv_path is None:
            # Default to skill's data directory
            csv_path = Path(__file__).parent.parent / 'data' / 'security_master.csv'
        self.csv_path = Path(csv_path)
        self.auto_discover = auto_discover

        # In-memory stores
        self._securities: Dict[str, Security] = {}  # primary_key -> Security
        self._ticker_index: Dict[str, str] = {}     # any_ticker -> primary_key

        # Load data
        self._load()

    # === Core Lookup Methods ===

    def get_security(self, identifier: str) -> Optional[Security]:
        """
        Get security by any identifier (uid, ISIN, ticker from any source).

        Args:
            identifier: uid, ISIN, or any ticker format

        Returns:
            Security object or None if not found
        """
        # Try direct uid lookup
        if identifier in self._securities:
            return self._securities[identifier]

        # Try ISIN format (convert to uid)
        if self._looks_like_isin(identifier):
            uid = f"isin_{identifier}"
            if uid in self._securities:
                return self._securities[uid]

        # Try ticker index (uppercase)
        primary_key = self._ticker_index.get(identifier.upper())
        if primary_key:
            return self._securities.get(primary_key)

        # Try lowercase for Stooq
        primary_key = self._ticker_index.get(identifier.lower())
        if primary_key:
            return self._securities.get(primary_key)

        return None

    def convert_ticker(
        self,
        ticker: str,
        from_source: Optional[SourceType] = None,
        to_source: SourceType = 'yahoo'
    ) -> Optional[str]:
        """
        Convert ticker from one source format to another.

        Args:
            ticker: Input ticker
            from_source: Source format (auto-detected if None)
            to_source: Target format

        Returns:
            Converted ticker or None if conversion not possible
        """
        security = self.get_security(ticker)
        if not security:
            # Try auto-discovery if looks like ISIN
            if self.auto_discover and self._looks_like_isin(ticker):
                security = self._discover_from_isin(ticker)

        if security:
            return security.get_ticker(to_source)
        return None

    def isin_to_ticker(self, isin: str, source: SourceType = 'yahoo') -> Optional[str]:
        """
        Convert ISIN to ticker for specified source.

        Args:
            isin: ISIN code
            source: Target source

        Returns:
            Ticker or None
        """
        return self.convert_ticker(isin, from_source=None, to_source=source)

    def ticker_to_isin(self, ticker: str) -> Optional[str]:
        """
        Get ISIN for a ticker.

        Args:
            ticker: Any ticker format

        Returns:
            ISIN or None
        """
        security = self.get_security(ticker)
        return security.isin if security else None

    def get_all_tickers(self, source: SourceType) -> Dict[str, str]:
        """
        Get all ticker mappings for a source.

        Args:
            source: Source name

        Returns:
            Dict mapping primary_key -> ticker
        """
        return {
            pk: sec.get_ticker(source)
            for pk, sec in self._securities.items()
            if sec.get_ticker(source)
        }

    # === Batch Operations ===

    def convert_tickers_batch(
        self,
        tickers: List[str],
        to_source: SourceType = 'yahoo'
    ) -> Dict[str, Optional[str]]:
        """
        Convert multiple tickers to target source format.

        Args:
            tickers: List of input tickers
            to_source: Target source

        Returns:
            Dict mapping input_ticker -> converted_ticker
        """
        return {t: self.convert_ticker(t, to_source=to_source) for t in tickers}

    def discover_missing_yahoo_tickers(
        self,
        isins: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Auto-discover Yahoo tickers for ISINs without mappings.

        Args:
            isins: Specific ISINs to lookup (None = all missing in registry)

        Returns:
            Dict of newly discovered ISIN -> Yahoo ticker mappings
        """
        if isins is None:
            # Find securities with ISIN but no Yahoo ticker
            isins = [
                sec.isin for sec in self._securities.values()
                if sec.isin and not sec.get_ticker('yahoo')
            ]

        discovered = {}
        for isin in isins:
            yahoo_ticker = self._lookup_yahoo_ticker(isin)
            if yahoo_ticker:
                discovered[isin] = yahoo_ticker
                uid = f"isin_{isin}"
                # Update in-memory if exists
                if uid in self._securities:
                    self._securities[uid].tickers['yahoo'] = yahoo_ticker
                    self._securities[uid].last_updated = datetime.now()
                    self._securities[uid].mapping_source = 'yahoo_api'
                    self._ticker_index[yahoo_ticker.upper()] = uid
                else:
                    # Create new security
                    security = self._create_security_from_discovery(isin, yahoo_ticker)
                    self.register_security(security)

        # Persist to CSV
        if discovered:
            self._save()

        return discovered

    # === Registration Methods ===

    def register_security(self, security: Security) -> None:
        """
        Add or update a security in the registry.

        Args:
            security: Security object to register
        """
        uid = security.uid
        if not uid:
            raise ValueError("Security must have uid")

        self._securities[uid] = security

        # Build ticker index - also index by ISIN if present
        if security.isin:
            self._ticker_index[security.isin] = uid

        # Index all tickers
        for source, ticker in security.tickers.items():
            if ticker:
                self._ticker_index[ticker.upper()] = uid
                if source == 'stooq':
                    self._ticker_index[ticker.lower()] = uid

    def add_ticker_mapping(
        self,
        identifier: str,
        source: SourceType,
        ticker: str,
        persist: bool = True
    ) -> bool:
        """
        Add a ticker mapping for an existing security.

        Args:
            identifier: ISIN or primary key
            source: Source name
            ticker: New ticker value
            persist: Whether to save to CSV

        Returns:
            True if mapping added successfully
        """
        security = self.get_security(identifier)
        if not security:
            return False

        security.tickers[source] = ticker
        security.last_updated = datetime.now()
        self._ticker_index[ticker.upper()] = security.primary_key

        if persist:
            self._save()

        return True

    # === Data Loading/Saving ===

    def _load(self) -> None:
        """Load data from CSV file."""
        if not self.csv_path.exists():
            print(f"[TickerRegistry] No CSV found at {self.csv_path}, starting empty")
            return

        try:
            with open(self.csv_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    security = Security.from_dict(row)
                    if security.primary_key:
                        self.register_security(security)

            print(f"[TickerRegistry] Loaded {len(self._securities)} securities from {self.csv_path}")

        except Exception as e:
            print(f"[TickerRegistry] Error loading CSV: {e}")

    def _save(self) -> None:
        """Save current state to CSV file."""
        # Ensure directory exists
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
                writer.writeheader()

                for security in self._securities.values():
                    writer.writerow(security.to_dict())

            print(f"[TickerRegistry] Saved {len(self._securities)} securities to {self.csv_path}")

        except Exception as e:
            print(f"[TickerRegistry] Error saving CSV: {e}")

    # === Yahoo API Integration ===

    def _lookup_yahoo_ticker(self, isin: str) -> Optional[str]:
        """
        Lookup Yahoo ticker via Yahoo search API.

        Uses YahooDirectFetcher.isin_to_ticker() internally.
        """
        try:
            from fetch_yahoo_direct import YahooDirectFetcher
            fetcher = YahooDirectFetcher(delay=0.5)
            ticker = fetcher.isin_to_ticker(isin)
            if ticker:
                print(f"[TickerRegistry] Discovered {isin} -> {ticker}")
            return ticker
        except Exception as e:
            print(f"[TickerRegistry] Yahoo lookup failed for {isin}: {e}")
            return None

    def _discover_from_isin(self, isin: str) -> Optional[Security]:
        """
        Create new security entry from ISIN via Yahoo lookup.
        """
        yahoo_ticker = self._lookup_yahoo_ticker(isin)
        if not yahoo_ticker:
            return None

        security = self._create_security_from_discovery(isin, yahoo_ticker)
        self.register_security(security)
        self._save()

        return security

    def _create_security_from_discovery(self, isin: str, yahoo_ticker: str) -> Security:
        """Create Security object from ISIN and discovered Yahoo ticker."""
        return Security(
            uid=f"isin_{isin}",
            isin=isin,
            name=f"[Auto] {yahoo_ticker}",
            instrument_type=self._infer_type_from_ticker(yahoo_ticker),
            country=isin[:2] if len(isin) >= 2 else '',
            exchange=self._infer_exchange_from_ticker(yahoo_ticker),
            tickers={'yahoo': yahoo_ticker},
            mapping_source='yahoo_api',
            last_updated=datetime.now()
        )

    # === Helper Methods ===

    def _looks_like_isin(self, s: str) -> bool:
        """Check if string looks like an ISIN (2 letters + 10 alphanumeric)."""
        return len(s) == 12 and s[:2].isalpha() and s[2:].isalnum()

    def _infer_type_from_ticker(self, yahoo_ticker: str) -> InstrumentType:
        """Infer instrument type from Yahoo ticker format."""
        if yahoo_ticker.startswith('^'):
            return 'index'
        if '=X' in yahoo_ticker:
            return 'currency'
        return 'equity'

    def _infer_exchange_from_ticker(self, yahoo_ticker: str) -> str:
        """Infer exchange from Yahoo ticker suffix."""
        if '.WA' in yahoo_ticker:
            return 'WSE'
        if '.L' in yahoo_ticker:
            return 'LSE'
        if '.DE' in yahoo_ticker:
            return 'XETRA'
        if '.' not in yahoo_ticker:
            return 'NYSE/NASDAQ'
        return ''

    # === Export Methods ===

    def to_dataframe(self) -> pd.DataFrame:
        """Export registry to DataFrame."""
        records = [sec.to_dict() for sec in self._securities.values()]
        return pd.DataFrame(records, columns=self.CSV_COLUMNS)

    def export_to_csv(self, path: Path) -> None:
        """Export registry to a different CSV file."""
        df = self.to_dataframe()
        df.to_csv(path, index=False)

    def __len__(self) -> int:
        return len(self._securities)

    def __repr__(self) -> str:
        return f"TickerRegistry({len(self._securities)} securities)"


# === Module-level convenience functions ===

_default_registry: Optional[TickerRegistry] = None


def get_default_registry() -> TickerRegistry:
    """Get or create default registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = TickerRegistry()
    return _default_registry


def convert_ticker(ticker: str, to_source: SourceType = 'yahoo') -> Optional[str]:
    """Quick ticker conversion using default registry."""
    return get_default_registry().convert_ticker(ticker, to_source=to_source)


def isin_to_yahoo(isin: str) -> Optional[str]:
    """Convert ISIN to Yahoo ticker."""
    return get_default_registry().isin_to_ticker(isin, source='yahoo')


def isin_to_stooq(isin: str) -> Optional[str]:
    """Convert ISIN to Stooq ticker."""
    return get_default_registry().isin_to_ticker(isin, source='stooq')


def ticker_to_isin(ticker: str) -> Optional[str]:
    """Get ISIN for any ticker."""
    return get_default_registry().ticker_to_isin(ticker)


if __name__ == '__main__':
    print("Testing TickerRegistry...")

    # Create registry
    registry = TickerRegistry()
    print(f"Loaded: {registry}")

    # Test ISIN discovery
    print("\nTesting ISIN discovery...")
    discovered = registry.discover_missing_yahoo_tickers(['PLXTRDM00011', 'PLCCC0000016'])
    print(f"Discovered: {discovered}")

    # Test lookups
    print("\nTesting lookups...")
    for isin in ['PLXTRDM00011', 'PLCCC0000016']:
        yahoo = registry.isin_to_ticker(isin, 'yahoo')
        print(f"  {isin} -> Yahoo: {yahoo}")

    # Export
    print("\nExporting to DataFrame...")
    df = registry.to_dataframe()
    print(df)
