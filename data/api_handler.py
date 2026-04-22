"""
API Handler
===========

Loads and provides typed access to API keys from api_holder.toml.

Dot-notation access:
    api = load_api_holder()
    api.bybit.real.api_key
    api.bybit.demo.rbr.api_key
    api.binance.real.api_key_1
    api.binance.testnet.api_key

Usage:
------
    from data.api_handler import load_api_holder

    holder = load_api_holder()
    api_key = holder.bybit.demo.rbr.api_key
    api_secret = holder.bybit.demo.rbr.api_secret
"""

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ApiKeys:
    """A single api_key / api_secret pair."""
    api_key: str = ""
    api_secret: str = ""

# =============================================================================
# BINANCE
# =============================================================================

@dataclass
class BinanceReal:
    """Two different pairs on main account."""
    _1: ApiKeys = field(default_factory=ApiKeys)
    _2: ApiKeys = field(default_factory=ApiKeys)

@dataclass
class Binance:
    """Binance account"""
    real: BinanceReal = field(default_factory=BinanceReal)
    testnet: ApiKeys = field(default_factory=ApiKeys)


# =============================================================================
# BYBIT
# =============================================================================


@dataclass
class BybitDemo:
    """Four different pairs on demo sub-accounts."""
    rbr: ApiKeys = field(default_factory=ApiKeys)
    rbd: ApiKeys = field(default_factory=ApiKeys)
    dbr: ApiKeys = field(default_factory=ApiKeys)
    dbd: ApiKeys = field(default_factory=ApiKeys)


@dataclass
class Bybit:
    """Bybit account"""
    real: ApiKeys = field(default_factory=ApiKeys)
    demo: BybitDemo = field(default_factory=BybitDemo)


# =============================================================================
# TOP-LEVEL HOLDER
# =============================================================================

@dataclass
class ApiHolder:
    """TOML API holder."""
    binance: Binance = field(default_factory=Binance)
    bybit: Bybit = field(default_factory=Bybit)


# =============================================================================
# LOADER
# =============================================================================

def load_api_holder(path: str = "data/api_holder.toml") -> ApiHolder:
    """
    Load API keys from a TOML file and return a typed ApiHolder.

    Args:
        path: Path to the TOML file (default: data/api_holder.toml)

    Returns:
        ApiHolder with all keys populated

    Raises:
        FileNotFoundError: If the TOML file does not exist
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"API holder file not found: {p}")

    with open(p, "rb") as f:
        raw = tomllib.load(f)

    bn = raw.get("binance", {})
    by = raw.get("bybit", {})

    bn_real = bn.get("real", {})
    by_demo = by.get("demo", {})

    return ApiHolder(
        binance=Binance(
            real=BinanceReal(
                _1=ApiKeys(**bn_real.get("_1", {})),
                _2=ApiKeys(**bn_real.get("_2", {})),
            ),
            testnet=ApiKeys(**bn.get("testnet", {})),
        ),
        bybit=Bybit(
            real=ApiKeys(**by.get("real", {})),
            demo=BybitDemo(
                rbr=ApiKeys(**by_demo.get("rbr", {})),
                rbd=ApiKeys(**by_demo.get("rbd", {})),
                dbr=ApiKeys(**by_demo.get("dbr", {})),
                dbd=ApiKeys(**by_demo.get("dbd", {})),
            ),
        ),
    )
