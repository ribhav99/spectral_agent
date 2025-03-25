"""
Collection of modular tools for the LLM trading agent.

Available tools:
- Twitter Sentiment: Analyzes crypto sentiment on Twitter
- Market Data: Fetches live trading data from Hyperliquid
- Trading Execution: Executes trades on Hyperliquid with integrated decision making
"""

from .twitter_sentiment import TwitterSentimentTool
from .market_data import MarketDataTool
from .trading_execution import TradingExecutionTool

# Map of tool names to their classes for dynamic loading
AVAILABLE_TOOLS = {
    "twitter_sentiment": TwitterSentimentTool,
    "market_data": MarketDataTool,
    "trading_execution": TradingExecutionTool
} 