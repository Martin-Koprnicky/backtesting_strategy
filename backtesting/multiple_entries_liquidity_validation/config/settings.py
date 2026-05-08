import tomllib

from pathlib import Path
from typing import Dict, List, Union, Any
from dataclasses import dataclass, field

@dataclass
class GeneralConfig:
    patterns: List[str] = field(default_factory=lambda: ["RBD", "DBD", "DBR", "RBR"])
    years: List[int] = field(default_factory=lambda: [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025])
    base_detection_timeframe: str = "1h"

@dataclass
class StrategyConfig:
    fixed_tp: bool = True
    price_level_tp: float = 2.2
    mountain_tp: bool = False
    full_zone_one_r: bool = True
    last_entry_one_r: bool = False

@dataclass
class BaseConfig:
    max_range: float = 2.2
    candle_count: List[int] = field(default_factory=lambda: [1,5])

@dataclass
class MovementBeforeConfig:
    candle_count: List[int] = field(default_factory=lambda: [1,5])
    movement_range: List[float] = field(default_factory=lambda: [0.5, 2])
    progressive_movement: bool = False
    body_min_percentage: float = 0.4
    min_strongest_candle_strength_score: float = 1
    min_weakest_candle_strength_score: float = 0.1

@dataclass
class MovementAfterConfig:
    candle_count: List[int] = field(default_factory=lambda: [1,5])
    movement_range: List[float] = field(default_factory=lambda: [0.5, 2])
    progressive_movement: bool = True
    body_min_percentage: float = 0.4
    min_strongest_candle_strength_score: float = 1
    min_weakest_candle_strength_score: float = 0.1

@dataclass
class LiquidityValidationConfig:
    validation: bool = True
    timeout_hours: int = 70
    retracement_percentage_min: float = 0.7
    retracement_percentage_max: float = 0.9
    wick_allowed_during_validation: bool = False

@dataclass
class TradingConfig:
    entry_timeout_hours: int = 100
    exit_timeout_hours: int = 500
    entry_levels: List[float] = field(default_factory=lambda: [1.0, 0.8, 0.6, 0.4, 0.2])
    entry_level_highlight: int = 1
    minus_base_range: bool = True
    stop_loss_moved: float = 0.01

@dataclass
class RiskConfig:
    capital: float = 1000
    zone_risk: float = 10
    entry_risk: float = 2

@dataclass
class FeesConfig:
    maker_fee: float = 0.0002
    taker_fee: float = 0.00055
    entry_threshold: float = 0.2


@dataclass
class Config:
    """
    Main configuration container.
    
    This holds all configuration sections and provides easy access.

    Attributes:
        general: General settings
        strategy: Current strategy configuration
        base: Base detection parameters
        movement_before: Movement before base validation parameters
        movement_after: Movement after base validation parameters
        liquidity_validation: Liquidity validation parameters
        trading: Trading configuration
        risk: Risk management parameters
    """
    general: GeneralConfig = field(default_factory=GeneralConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    base: BaseConfig = field(default_factory=BaseConfig)
    movement_before: MovementBeforeConfig = field(default_factory=MovementBeforeConfig)
    movement_after: MovementAfterConfig = field(default_factory=MovementAfterConfig)
    liquidity: LiquidityValidationConfig = field(default_factory=LiquidityValidationConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    fees: FeesConfig = field(default_factory=FeesConfig)

    # Store raw dict for any values we didn't explicity define
    _raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    def get(self, section: str, key: str, default: Any = None) -> None:
        """
        Get a raw config value by section and key.

        Useful for accessing values that aren't in the typed config classes.

        Args:
            section: Config section name
            key: Key within the setcion
            default: Default value if not found

        Returns:
            The config value or default
        """
        try:
            return self._raw.get(section, {}).get(key, default)
        except (KeyError, TypeError):
            return default


def load_config(config_path: Union[str, Path]) -> Config:
    """
    Load configuration from a TOML file.

    This is the main function to use to load config.

    Args:
        config_path: Path to the TOML configuration file
    
    Returns:
        Config object with all settings loaded

    Raises:
        FileNotFoundError: If config file weren't found
        tomllib.TOMLDecodeError: If TOML syntax is invalid
    """

    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, 'rb') as file:
        raw_config = tomllib.load(file)

    config = _build_config(raw_config)

    return config

def _build_config(raw: Dict[str, Any]) -> Config:
    """
    Build a Config object from a raw dictionary.

    This helper function converts the raw TOML dict into our typed Config

    Args:
        raw: Dictionary from parsing TOML
    
    Returns:
        Typed Config object
    """
    # Helper to safety get a section from raw config
    def get_section(name: str) -> Dict[str, Any]:
        return raw.get(name, {})
    
    # Build Config object

    config = Config(
        general=GeneralConfig(**get_section('general')),
        strategy=StrategyConfig(**get_section('strategy')),
        base=BaseConfig(**get_section('base')),
        movement_before=MovementBeforeConfig(**get_section('movement_before')),
        movement_after=MovementAfterConfig(**get_section('movement_after')),
        liquidity=LiquidityValidationConfig(**get_section('liquidity_validation')),
        trading=TradingConfig(**get_section('trading')),
        risk=RiskConfig(**get_section('risk')),
        fees=FeesConfig(**get_section('fees')),
    )

    return config

def get_default_config() -> Config:
    """
    Get the default configuration.

    Tris to load from the default config file, falls back to hardcoded defaults.

    Returns:
        Config object tiwht default settings
    """
    # Try to find the default config file
    possible_paths = [
        Path(__file__).parent / 'default_config.toml',
        Path('backtesting/config/default_config.toml'),
        Path('default_config.toml'),
    ]

    for path in possible_paths:
        if path.exists():
            config = load_config(path)
            return config
        
    # If no file found, return config with all defaults
    config = Config()
    return config
