"""Market data tool for fetching real data from Hyperliquid API."""

import time
import json
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import logging
import os
import random

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import eth_account

from ..utils.logger import setup_logger
from .. import config

logger = setup_logger("market_data_tool")

class MarketDataTool:
    """Tool for fetching market data from Hyperliquid."""
    
    def __init__(self):
        """Initialize the market data tool."""
        self.name = "Market Data"
        self.description = "Fetches live trading data from Hyperliquid"
        self.use_real_api = config.USE_REAL_API
        self.retry_count = 2  # Number of retries for API requests
        
        # Select the appropriate API URL
        self.api_url = constants.TESTNET_API_URL
        
        if not self.use_real_api:
            logger.info("Market data tool initialized in synthetic data mode")
        else:
            logger.info(f"Market data tool initialized with Hyperliquid API: {self.api_url}")
    
    def _setup_connection(self):
        """Set up connection to Hyperliquid API."""
        try:
            # Create Info instance without WebSocket connection
            info = Info(self.api_url, skip_ws=True)
            
            # Create a wallet if we have a private key from environment variable
            private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
            if private_key:
                account = eth_account.Account.from_key(private_key)
                exchange = Exchange(account, self.api_url)
                logger.debug(f"Connected to Hyperliquid with address: {account.address}")
            else:
                exchange = None
                logger.debug("No private key provided, read-only mode")
                
            return info, exchange
        except Exception as e:
            logger.error(f"Error setting up Hyperliquid connection: {str(e)}")
            raise
    
    def run(self, symbol: str = "ETH", timeframe: str = "1h") -> Dict[str, Any]:
        """
        Fetch market data for a crypto asset.
        
        Args:
            symbol: Cryptocurrency symbol to analyze
            timeframe: Timeframe for OHLC data ('1m', '5m', '15m', '1h', '4h', '1d')
            
        Returns:
            Dictionary with market data or error information
        """
        # Normalize symbol (uppercase)
        symbol = symbol.upper()
        
        # Check if we should use real API
        if not self.use_real_api:
            logger.info(f"Using synthetic data for {symbol} (USE_REAL_API=False)")
            # Generate synthetic data since real API is disabled
            return self._generate_realistic_market_data(symbol, timeframe)
        
        logger.info(f"Fetching market data for {symbol} on {timeframe} timeframe")
        
        try:
            # Set up connection to Hyperliquid
            info, _ = self._setup_connection()
            
            # Get market metadata
            meta = info.meta()
            
            # Get market information and price
            market_info = self._get_market_info(info, symbol)
            if not market_info:
                return {
                    "symbol": symbol,
                    "status": "error",
                    "message": f"Failed to fetch market info for {symbol}",
                    "timestamp": int(time.time())
                }
            
            # Get candles
            candles = self._get_candles(info, symbol, timeframe)
            if not candles:
                return {
                    "symbol": symbol,
                    "status": "error",
                    "message": f"Failed to fetch candle data for {symbol}",
                    "timestamp": int(time.time())
                }
            
            # Calculate indicators from candle data
            indicators = self._calculate_indicators(candles)
            
            # Construct the response
            result = {
                "symbol": symbol,
                "current_price": market_info.get("mark_price"),
                "24h_change_percent": market_info.get("24h_change", 0),
                "24h_volume": market_info.get("24h_volume", 0),
                "funding_rate": market_info.get("funding_rate", 0),
                "open_interest": market_info.get("open_interest", 0),
                "timeframe": timeframe,
                "indicators": indicators,
                "timestamp": int(time.time())
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            return {
                "symbol": symbol,
                "status": "error",
                "message": f"Error fetching market data: {str(e)}",
                "timestamp": int(time.time())
            }
    
    def _get_market_info(self, info: Info, symbol: str) -> Dict[str, Any]:
        """
        Get market information for a symbol.
        
        Args:
            info: Hyperliquid Info instance
            symbol: Market symbol
            
        Returns:
            Dictionary with market information
        """
        for attempt in range(self.retry_count):
            try:
                # Get all market mids (prices)
                all_mids = info.all_mids()
                
                # Get market metadata and context
                meta_and_asset_ctxs = info.meta_and_asset_ctxs()
                meta, asset_ctxs = meta_and_asset_ctxs
                
                # Find the matching asset
                symbol_idx = None
                for idx, asset in enumerate(meta["universe"]):
                    if asset["name"] == symbol:
                        symbol_idx = idx
                        break
                
                if symbol_idx is None:
                    logger.warning(f"Symbol {symbol} not found in market list")
                    if attempt < self.retry_count - 1:
                        time.sleep(1)
                        continue
                    return {}
                
                # Get asset context
                asset_ctx = asset_ctxs[symbol_idx]
                
                # Extract market data
                mark_price = float(asset_ctx.get("markPx", 0))
                mid_price = float(asset_ctx.get("midPx", 0)) if asset_ctx.get("midPx") else mark_price
                prev_day_price = float(asset_ctx.get("prevDayPx", 0))
                
                # Calculate 24h change
                if prev_day_price > 0:
                    day_change = ((mark_price - prev_day_price) / prev_day_price) * 100
                else:
                    day_change = 0
                
                # Return market data
                return {
                    "mark_price": mark_price,
                    "mid_price": mid_price,
                    "24h_change": day_change,
                    "24h_volume": float(asset_ctx.get("dayNtlVlm", 0)),
                    "funding_rate": float(asset_ctx.get("funding", 0)),
                    "open_interest": float(asset_ctx.get("openInterest", 0))
                }
                
            except Exception as e:
                logger.error(f"Error in _get_market_info: {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(1)
        
        return {}
    
    def _get_candles(self, info: Info, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """
        Get historical candle data for a symbol.
        
        Args:
            info: Hyperliquid Info instance
            symbol: Market symbol
            timeframe: Candle timeframe
            
        Returns:
            List of candle data
        """
        for attempt in range(self.retry_count):
            try:
                # Convert timeframe to interval
                interval_map = {
                    "1m": "1m",
                    "5m": "5m",
                    "15m": "15m",
                    "1h": "1h", 
                    "4h": "4h",
                    "1d": "1d"
                }
                
                interval = interval_map.get(timeframe, "1h")  # Default to 1h
                
                # Calculate time range (last 100 candles)
                end_time = int(time.time() * 1000)  # Convert to milliseconds
                
                # Calculate start time based on interval
                seconds_map = {
                    "1m": 60,
                    "5m": 300,
                    "15m": 900,
                    "1h": 3600,
                    "4h": 14400,
                    "1d": 86400
                }
                seconds = seconds_map.get(interval, 3600)
                start_time = end_time - (seconds * 1000 * 100)  # 100 candles
                
                # Get candle data
                candles = info.candles_snapshot(symbol, interval, start_time, end_time)
                
                if not candles:
                    logger.warning(f"No candle data returned for {symbol} on {interval} (attempt {attempt+1}/{self.retry_count})")
                    if attempt < self.retry_count - 1:
                        time.sleep(1)
                        continue
                    return []
                
                # Format candles to a standard format
                formatted_candles = []
                for candle in candles:
                    formatted_candles.append({
                        "time": int(candle["t"] / 1000),  # Convert ms to seconds
                        "open": float(candle["o"]),
                        "high": float(candle["h"]),
                        "low": float(candle["l"]),
                        "close": float(candle["c"]),
                        "volume": float(candle["v"])
                    })
                
                return formatted_candles
                
            except Exception as e:
                logger.error(f"Error in _get_candles: {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(1)
        
        return []
    
    def _calculate_indicators(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate technical indicators from candle data."""
        if not candles:
            return {}
            
        try:
            # Convert candles to DataFrame
            df = pd.DataFrame(candles)
            
            # Convert timestamp to datetime
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Calculate basic indicators
            # SMA - Simple Moving Average
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            # EMA - Exponential Moving Average
            df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
            
            # MACD - Moving Average Convergence Divergence
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
            
            # RSI - Relative Strength Index
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df['rsi_14'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            df['bb_std'] = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
            df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
            
            # Volatility (using ATR - Average True Range)
            df['tr'] = np.maximum(
                np.maximum(
                    df['high'] - df['low'],
                    abs(df['high'] - df['close'].shift(1))
                ),
                abs(df['low'] - df['close'].shift(1))
            )
            df['atr_14'] = df['tr'].rolling(window=14).mean()
            
            # Get the latest values
            latest = df.iloc[-1].to_dict()
            
            # Extract relevant indicators
            indicators = {
                'sma_20': latest.get('sma_20'),
                'sma_50': latest.get('sma_50'),
                'ema_12': latest.get('ema_12'),
                'ema_26': latest.get('ema_26'),
                'macd': latest.get('macd'),
                'macd_signal': latest.get('macd_signal'),
                'macd_hist': latest.get('macd_hist'),
                'rsi_14': latest.get('rsi_14'),
                'bb_upper': latest.get('bb_upper'),
                'bb_middle': latest.get('bb_middle'),
                'bb_lower': latest.get('bb_lower'),
                'atr_14': latest.get('atr_14'),
            }
            
            # Remove NaN values
            return {k: v for k, v in indicators.items() if pd.notna(v)}
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return {}
    
    def _generate_realistic_market_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Generate realistic synthetic market data for testing purposes."""
        # Base prices for popular cryptocurrencies
        base_prices = {
            "BTC": 48000,
            "ETH": 2800,
            "SOL": 110,
            "AVAX": 35,
            "DOT": 8,
            "LINK": 18,
            "ADA": 0.5,
            "XRP": 0.6,
            "BNB": 480,
            "MATIC": 0.9,
            "DOGE": 0.09,
            "SHIB": 0.00001,
            "PEPE": 0.00001,
            "NEAR": 6,
            "OP": 3,
            "ARB": 1.5,
        }
        
        # Use the base price or generate a random one
        current_price = base_prices.get(symbol, round(random.uniform(0.1, 100), 2))
        
        # Add some randomness to the price
        current_price = current_price * (1 + np.random.normal(0, 0.02))
        
        # Generate a realistic 24h change
        change_24h = np.random.normal(0, 3)  # Mean 0%, std 3%
        
        # Generate volume based on popularity
        if symbol in ["BTC", "ETH"]:
            volume = np.random.uniform(500_000_000, 2_000_000_000)
        elif symbol in ["SOL", "AVAX", "DOT", "LINK", "ADA", "XRP", "BNB"]:
            volume = np.random.uniform(50_000_000, 500_000_000)
        else:
            volume = np.random.uniform(1_000_000, 50_000_000)
        
        # Generate funding rate (typically between -0.1% and 0.1%)
        funding_rate = np.random.normal(0, 0.0005)
        
        # Generate open interest
        open_interest = volume * np.random.uniform(0.1, 0.5)
        
        # Generate indicator values
        indicators = {
            'sma_20': current_price * (1 + np.random.normal(0, 0.03)),
            'sma_50': current_price * (1 + np.random.normal(0, 0.05)),
            'ema_12': current_price * (1 + np.random.normal(0, 0.02)),
            'ema_26': current_price * (1 + np.random.normal(0, 0.04)),
            'macd': np.random.normal(0, current_price * 0.01),
            'macd_signal': np.random.normal(0, current_price * 0.01),
            'macd_hist': np.random.normal(0, current_price * 0.005),
            'rsi_14': np.random.uniform(30, 70),
            'bb_upper': current_price * (1 + np.random.uniform(0.01, 0.05)),
            'bb_middle': current_price,
            'bb_lower': current_price * (1 - np.random.uniform(0.01, 0.05)),
            'atr_14': current_price * np.random.uniform(0.01, 0.03),
        }
        
        # Format and return synthetic data
        return {
            "symbol": symbol,
            "current_price": round(current_price, 8),
            "24h_change_percent": round(change_24h, 2),
            "24h_volume": round(volume, 2),
            "funding_rate": round(funding_rate, 6),
            "open_interest": round(open_interest, 2),
            "timeframe": timeframe,
            "indicators": {k: round(v, 6) for k, v in indicators.items()},
            "timestamp": int(time.time()),
            "is_synthetic": True
        } 