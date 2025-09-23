import os
import dataclasses
import typing
from datetime import datetime


@dataclasses.dataclass
class Config:
    grok_api_key: str = dataclasses.field(default_factory=lambda: os.getenv("GROK_API_KEY", ""))
    alpaca_api_key: str = dataclasses.field(default_factory=lambda: os.getenv("APCA_API_KEY_ID", ""))
    alpaca_secret: str = dataclasses.field(default_factory=lambda: os.getenv("APCA_API_SECRET_KEY", ""))
    interval: int = dataclasses.field(default_factory=lambda: int(os.getenv("INTERVAL", "5")))
    disable_grok: bool = dataclasses.field(default_factory=lambda: os.getenv("DISABLE_GROK", "false").lower() == "true")
    cors_origins: typing.List[str] = dataclasses.field(default_factory=lambda: [os.getenv("CORS_ORIGINS", "http://localhost:5173")])

    def __post_init__(self):
        if not self.grok_api_key:
            raise ValueError("GROK_API_KEY environment variable is required")
        if not self.alpaca_api_key:
            raise ValueError("APCA_API_KEY_ID environment variable is required")
        if not self.alpaca_secret:
            raise ValueError("APCA_API_SECRET_KEY environment variable is required")
        if self.interval <= 0:
            raise ValueError("INTERVAL must be a positive integer")
        # Parse CORS_ORIGINS as comma-separated list
        origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        self.cors_origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]