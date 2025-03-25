import os
import json
import dotenv
import logging
from pathlib import Path

# Load environment variables from .env file
dotenv.load_dotenv()

# API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")

# Hyperliquid configuration - only from environment variable
HYPERLIQUID_PRIVATE_KEY = os.getenv("HYPERLIQUID_PRIVATE_KEY")

# Trading parameters
DEFAULT_POSITION_SIZE = float(os.getenv("DEFAULT_POSITION_SIZE", "0.01"))  # 1% of available balance
DEFAULT_STOP_LOSS_PERCENT = float(os.getenv("DEFAULT_STOP_LOSS_PERCENT", "0.02"))  # 2% stop loss

# API endpoints - prioritize env vars
HYPERLIQUID_API_TESTNET = os.getenv("HYPERLIQUID_API_TESTNET", "https://api.hyperliquid-testnet.xyz/v1")
HYPERLIQUID_API_MAINNET = os.getenv("HYPERLIQUID_API_MAINNET", "https://api.hyperliquid.xyz/v1")

# Environment settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Flag to enable/disable real API calls (useful for testing)
USE_REAL_API = os.getenv("USE_REAL_API", "true").lower() == "true"

# Display configuration on startup
def display_config_info():
    """Display configuration information for debugging"""
    if ENVIRONMENT == "development":
        print("\nConfiguration:")
        print(f"- Environment: {ENVIRONMENT}")
        print(f"- Log Level: {LOG_LEVEL}")
        print(f"- Hyperliquid API: {'Enabled' if USE_REAL_API else 'Disabled (using synthetic data)'}")
        print(f"- Hyperliquid Testnet API: {HYPERLIQUID_API_TESTNET}")
        print(f"- OpenAI API: {'Configured' if OPENAI_API_KEY else 'Not configured'}")
        print(f"- Private Key: {'Configured' if HYPERLIQUID_PRIVATE_KEY else 'Not configured'}")
        print(f"- Position Size: {DEFAULT_POSITION_SIZE * 100}%")
        print(f"- Stop Loss: {DEFAULT_STOP_LOSS_PERCENT * 100}%\n") 