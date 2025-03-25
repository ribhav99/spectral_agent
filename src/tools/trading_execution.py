"""Trading execution tool for executing trades on Hyperliquid."""

import time
import json
from typing import Dict, List, Any, Optional, Union, Tuple
import base64
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
import hmac
import hashlib

from ..utils.logger import setup_logger
from .. import config

# Set up logger
logger = setup_logger("trading_execution_tool")

# Import the hyperliquid SDK
try:
    import eth_account
    from eth_account.messages import encode_defunct
    from hyperliquid.exchange import Exchange
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
except ImportError:
    logger.warning("hyperliquid-python-sdk not installed. Run: pip install hyperliquid-python-sdk")

class TradingExecutionTool:
    """Tool for executing trades on Hyperliquid based on decisions."""
    
    def __init__(self):
        """Initialize the trading execution tool."""
        self.name = "Trading Execution"
        self.description = "Executes trades on Hyperliquid based on decisions"
        
        # Initialize trading connection
        # Use mainnet since the wallet is registered there
        self.base_url = constants.MAINNET_API_URL
        self.private_key = config.HYPERLIQUID_PRIVATE_KEY
        self.wallet_address = None
        
        logger.info(f"Initializing TradingExecutionTool with API URL: {self.base_url}")
        
        # Setup SDK-related attributes
        self.exchange = None
        self.info = None
        
        # Initialize if private key is available
        if self.private_key:
            try:
                # Create account from private key
                account = eth_account.Account.from_key(self.private_key)
                self.wallet_address = account.address
                logger.info(f"Initialized wallet with address: {self.wallet_address}")
                
                # Initialize Info client for market data
                try:
                    self.info = Info(self.base_url, skip_ws=True)
                    logger.info("Initialized info client successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Info client: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to initialize wallet: {str(e)}")
        else:
            logger.warning("No private key found, trading execution will run in simulation mode")
    
    def run(self, 
            symbol: str = "BTC",
            direction: str = None,
            position_size: float = None,
            stop_loss: float = None,
            take_profit: float = None,
            amount: float = 100.0,
            market_data: Dict[str, Any] = None,
            sentiment_data: Dict[str, Any] = None,
            dry_run: bool = True) -> Dict[str, Any]:
        """
        Execute a trading strategy based on parameters

        Args:
            symbol: Trading pair symbol
            direction: 'LONG', 'SHORT', or None (to use sentiment-based decision)
            position_size: Size as percentage of available margin
            stop_loss: Stop loss percentage (not used)
            take_profit: Take profit percentage (not used)
            amount: Dollar amount to trade
            market_data: Market data
            sentiment_data: Sentiment data
            dry_run: Whether to execute in dry run mode

        Returns:
            Trading result dict
        """
        logger.info(f"💰 Trading execution for {symbol} with amount: ${amount} (dry_run: {dry_run})")
        
        # Check minimum trade amount - log but don't throw error in dry run
        MIN_TRADE_AMOUNT = 10.0
        if amount < MIN_TRADE_AMOUNT:
            logger.warning(f"⚠️ Amount ${amount} is below minimum ${MIN_TRADE_AMOUNT} - orders may be rejected")
            if not dry_run:
                return {
                    "symbol": symbol,
                    "direction": direction if direction else "NEUTRAL",
                    "status": "failed",
                    "error": f"Amount ${amount} is below minimum ${MIN_TRADE_AMOUNT}",
                    "timestamp": int(time.time())
                }
        
        # If direction is provided, use it
        if direction:
            trade_direction = direction.upper()
            logger.info(f"Using provided direction: {trade_direction}")
        else:
            # Make decision based on sentiment/market data
            trade_decision = self._make_trading_decision(symbol, market_data, sentiment_data)
            trade_direction = trade_decision["direction"]
            logger.info(f"Generated direction: {trade_direction} (based on sentiment/market analysis)")
            
        # Create simplified decision dict (no stop loss or take profit)
        custom_decision = {
            "symbol": symbol,
            "decision": trade_direction
        }
        
        # Execute the trade with market order only
        logger.info(f"🚀 Executing {trade_direction} trade for {symbol} with ${amount}")
        result = self.execute_trade(custom_decision, dry_run=dry_run, amount=amount, market_data=market_data)
        
        return result
    
    def execute_trade(self, 
                     decision: Dict[str, Any],
                     dry_run: bool = False,
                     amount: float = 100.0,
                     market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a trade based on the decision

        Args:
            decision: Trading decision with direction
            dry_run: Whether to simulate the execution
            amount: Dollar amount to trade
            market_data: Market data for the symbol

        Returns:
            Execution result
        """
        symbol = decision.get("symbol", "BTC")
        direction = decision.get("decision", "NEUTRAL")
        
        # Skip if direction is NEUTRAL
        if direction == "NEUTRAL":
            logger.info(f"NEUTRAL direction - no trade will be executed for {symbol}")
            return {
                "symbol": symbol,
                "direction": direction,
                "status": "not_executed",
                "reason": "Neutral recommendation",
                "timestamp": int(time.time())
            }

        logger.info(f"Executing {direction} trade for {symbol} with amount: ${amount}")
        
        # Get market price
        current_price = self._get_market_price(symbol)
        
        # Calculate size in asset units (e.g., ETH)
        size = amount / current_price
        # Round to 4 decimal places
        size = round(size, 4)
        
        # Place the market order only (no stop loss or take profit)
        entry_result = self._place_order(
            symbol=symbol, 
            side="b" if direction == "LONG" else "a", 
            size=size, 
            order_type="market",
            dry_run=dry_run
        )
        
        # Extract order details
        order_id = "unknown"
        executed_price = current_price
        executed_size = size
        
        try:
            if "response" in entry_result and "data" in entry_result["response"]:
                filled_order = entry_result["response"]["data"]["statuses"][0].get("filled", {})
                order_id = filled_order.get("oid", "unknown")
                executed_price = filled_order.get("avgPx", current_price)
                executed_size = filled_order.get("totalSz", size)
                logger.info(f"Order executed at price: ${executed_price} for size: {executed_size}")
            elif dry_run:
                order_id = "dry-run-" + str(int(time.time()))
        except Exception as e:
            logger.warning(f"Could not extract complete order details: {e}")
        
        # Return simplified result
        result = {
            "symbol": symbol,
            "direction": direction,
            "order_id": order_id,
            "status": "executed" if entry_result.get("status") == "ok" else "failed",
            "price": executed_price,
            "size": executed_size,
            "amount": amount,
            "timestamp": int(time.time())
        }
        
        # Include error details if order failed
        if entry_result.get("status") != "ok":
            result["error"] = entry_result.get("message", "Unknown error")
            result["details"] = entry_result
            
        logger.info(f"Trade execution completed: {result}")
        return result
    
    def _get_market_price(self, symbol: str, retry_count: int = 0) -> Optional[float]:
        """Get current market price for a symbol using the Hyperliquid SDK."""
        try:
            # Create a standalone Info client if we don't have one
            if not hasattr(self, 'info') or self.info is None:
                logger.debug("Creating new Info client for market data")  # Changed from info to debug
                self.info = Info(self.base_url, skip_ws=True)
            
            # Reduce log level 
            logger.debug(f"Fetching market price for {symbol}")  # Changed from info to debug
            
            # For dry runs, just return a reasonable default price to reduce API calls
            if retry_count > 0:
                # Use sensible defaults for testing
                default_prices = {
                    "BTC": 60000,
                    "ETH": 3000,
                    "SOL": 100,
                    "AVAX": 35
                }
                clean_symbol = self._format_symbol(symbol)
                return default_prices.get(clean_symbol, 2000)
                
            # Call the all_mids method to get current prices
            all_mids = self.info.all_mids()
            
            # Clean the symbol if needed
            clean_symbol = symbol
            if "-PERP" in symbol:
                clean_symbol = symbol.replace("-PERP", "")
            
            # Check if the symbol exists in the returned data
            if clean_symbol in all_mids:
                price = float(all_mids[clean_symbol])
                logger.info(f"Got price for {clean_symbol}: ${price}")
                return price
            else:
                # Log all available symbols for debugging
                logger.warning(f"Symbol {clean_symbol} not found in market data. Available symbols: {list(all_mids.keys())}")
                
            # Retry logic if price not found
            if retry_count < 2:
                logger.info(f"Retrying market price fetch for {symbol} (attempt {retry_count + 1})")
                time.sleep(1)  # Brief delay before retry
                return self._get_market_price(symbol, retry_count + 1)
                
            # Return a default value for testing purposes if all else fails
            logger.warning(f"Unable to get market price for {symbol}, using default test value")
            return 2000  # Default value for ETH price
            
        except Exception as e:
            logger.error(f"Error getting market price: {str(e)}")
            if retry_count < 2:
                logger.info(f"Retrying after error (attempt {retry_count + 1})")
                time.sleep(1)
                return self._get_market_price(symbol, retry_count + 1)
            return 2000  # Default value for testing
    
    def _get_account_balance(self) -> float:
        """Get account balance (USD)."""
        try:
            if not self.wallet_address:
                # Return sample balance for testing
                return 10000
            
            endpoint = f"{self.base_url}/user"
            params = {"address": self.wallet_address}
            response = requests.get(endpoint, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return float(data.get("margin_summary", {}).get("total_margin_usd", 0))
            
            logger.warning("Could not get account balance")
            return 10000  # Default value for testing
            
        except Exception as e:
            logger.error(f"Error getting account balance: {str(e)}")
            return 10000  # Default value for testing
    
    def _place_order(self, symbol: str, side: str, size: float, order_type: str = "market", price: float = None, reduce_only: bool = False, dry_run: bool = False) -> dict:
        """
        Place an order on Hyperliquid

        Args:
            symbol: Trading pair
            side: 'b' for buy, 'a' for sell
            size: Position size in asset units
            order_type: 'market' or 'limit'
            price: Limit price (only for limit orders)
            reduce_only: Whether the order should only reduce position
            dry_run: Whether to simulate the order without execution

        Returns:
            Order result
        """
        try:
            if dry_run:
                logger.info(f"DRY RUN: Would execute {order_type} {'buy' if side == 'b' else 'sell'} for {size} {symbol}")
                # Simple dry run response to reduce clutter
                return {
                    "status": "ok",
                    "response": {"type": "success", "data": {"statuses": [{"filled": {"oid": int(time.time()), "totalSz": size, "avgPx": price or self._get_market_price(symbol)}}]}},
                    "dry_run": True
                }

            # Initialize exchange connection
            if not self.exchange:
                self._init_exchange()

            # Format the symbol for Hyperliquid
            clean_symbol = self._format_symbol(symbol)
            logger.info(f"Placing order for symbol: {clean_symbol}")
            
            # Check if order size is sufficient (minimum $10)
            current_price = self._get_market_price(symbol)
            order_value = size * current_price
            
            if order_value < 10.5:  # Add buffer to ensure minimum is met
                logger.warning(f"Order value ${order_value} is below minimum $10. Adjusting size.")
                # Adjust size to meet minimum
                minimum_size = 10.5 / current_price
                size = round(minimum_size, 4)
                logger.info(f"Adjusted size to {size} to meet minimum order value")

            is_buy = (side == "b")
            logger.info(f"Order direction: {'Buy' if is_buy else 'Sell'}, Size: {size}, Type: {order_type}")

            # Execute market orders using market_open
            if order_type == "market":
                logger.info(f"Executing market order for {clean_symbol}: {'Buy' if is_buy else 'Sell'} {size}")
                if reduce_only:
                    # For closing positions, use market_close
                    logger.info(f"Closing position for {clean_symbol}")
                    result = self.exchange.market_close(clean_symbol)
                else:
                    # For opening positions, use market_open
                    logger.info(f"Opening position for {clean_symbol} with size {size}")
                    
                    # Use reasonable slippage protection (1%)
                    slippage = 0.01
                    result = self.exchange.market_open(clean_symbol, is_buy, size, None, slippage)
                
                logger.info(f"Market order result: {result}")
                return result
                
            # Use order for limit orders
            elif order_type == "limit" and price is not None:
                # Round price to 2 decimal places for better compatibility with exchange requirements
                price = round(price, 2)
                logger.info(f"Executing limit order for {clean_symbol} at price {price}")
                
                # Use positional arguments instead of named arguments
                result = self.exchange.order(
                    clean_symbol,  # coin
                    is_buy,        # is_buy
                    size,          # sz
                    price,         # limit_px
                    None,          # cloid
                    reduce_only    # reduce_only
                )
                logger.info(f"Limit order result: {result}")
                return result
                
            else:
                logger.error(f"Invalid order type or missing price: {order_type}")
                return {"status": "error", "message": "Invalid order type or missing price"}
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error placing order: {error_msg}")
            
            # Enhance error details
            error_details = {
                "error": error_msg,
                "symbol": symbol,
                "side": side,
                "size": size,
                "order_type": order_type,
                "price": price,
                "reduce_only": reduce_only
            }
            
            return {"status": "error", "message": error_msg, "details": error_details}
    
    def _make_trading_decision(self, symbol: str, market_data: Dict[str, Any] = None, sentiment_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make a trading decision based on market data and sentiment.
        
        Args:
            symbol: Cryptocurrency symbol
            market_data: Market data dictionary
            sentiment_data: Sentiment analysis dictionary
            
        Returns:
            Dictionary with trading decision
        """
        logger.info(f"Making trading decision for {symbol}")
        
        # Default to neutral if no data available
        if not market_data and not sentiment_data:
            logger.warning("No market or sentiment data available for decision making")
            return {
                "direction": "NEUTRAL",
                "confidence": 0.0,
                "reasoning": "Insufficient data for trading decision"
            }
            
        # Factors to consider (with default values)
        sentiment_score = 0.0
        price_change_24h = 0.0
        rsi = 50.0  # Neutral RSI
        
        # Extract sentiment data if available
        if sentiment_data and isinstance(sentiment_data, dict):
            sentiment_score = sentiment_data.get("average_sentiment", 0.0)
            logger.info(f"Using sentiment score: {sentiment_score}")
            
        # Extract market data if available
        if market_data and isinstance(market_data, dict):
            price_change_24h = market_data.get("24h_change_percent", 0.0)
            indicators = market_data.get("indicators", {})
            if indicators:
                rsi = indicators.get("rsi_14", indicators.get("rsi", 50.0))
            logger.info(f"Using market data - 24h change: {price_change_24h}%, RSI: {rsi}")
            
        # Simple decision logic
        # 1. If sentiment is strongly positive (>0.5) and RSI is not overbought (<70), go LONG
        # 2. If sentiment is strongly negative (<-0.5) and RSI is not oversold (>30), go SHORT
        # 3. If RSI shows overbought (>80) and price increase >5%, go SHORT regardless of sentiment
        # 4. If RSI shows oversold (<20) and price decrease >5%, go LONG regardless of sentiment
        # 5. Otherwise, stay NEUTRAL
        
        reasoning_points = []
        
        if rsi > 80 and price_change_24h > 5:
            direction = "SHORT"
            confidence = 0.8
            reasoning_points.append(f"RSI is overbought at {rsi}")
            reasoning_points.append(f"Price increased {price_change_24h}% in 24h")
            
        elif rsi < 20 and price_change_24h < -5:
            direction = "LONG"
            confidence = 0.8
            reasoning_points.append(f"RSI is oversold at {rsi}")
            reasoning_points.append(f"Price decreased {abs(price_change_24h)}% in 24h")
            
        elif sentiment_score > 0.5 and rsi < 70:
            direction = "LONG"
            confidence = 0.7
            reasoning_points.append(f"Sentiment is bullish at {sentiment_score}")
            reasoning_points.append(f"RSI is not overbought at {rsi}")
            
        elif sentiment_score < -0.5 and rsi > 30:
            direction = "SHORT"
            confidence = 0.7
            reasoning_points.append(f"Sentiment is bearish at {sentiment_score}")
            reasoning_points.append(f"RSI is not oversold at {rsi}")
            
        else:
            # Default to neutral if no strong signals
            direction = "NEUTRAL"
            confidence = 0.5
            reasoning_points.append("No strong signals detected")
            reasoning_points.append(f"Sentiment: {sentiment_score}, RSI: {rsi}, 24h change: {price_change_24h}%")
            
        reasoning = ". ".join(reasoning_points)
        logger.info(f"Trading decision: {direction} with confidence {confidence} - {reasoning}")
        
        return {
            "direction": direction,
            "confidence": confidence,
            "reasoning": reasoning
        }
    
    def _init_exchange(self):
        """Initialize the exchange connection using the Hyperliquid SDK."""
        if self.exchange is not None:
            logger.info("Exchange connection already initialized")
            return
            
        try:
            if not self.private_key:
                logger.error("No private key configured for trading")
                return
                
            # Create account from private key
            account = eth_account.Account.from_key(self.private_key)
            self.wallet_address = account.address
            logger.info(f"Initializing exchange with wallet address: {self.wallet_address}")
            
            # Initialize exchange client
            self.exchange = Exchange(account, self.base_url)
            logger.info(f"Exchange client initialized with API URL: {self.base_url}")
            
            # Initialize info client if not already done
            if self.info is None:
                self.info = Info(self.base_url, skip_ws=True)
                logger.info("Info client initialized for market data")
                
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {str(e)}")
            raise 

    def _format_symbol(self, symbol: str) -> str:
        """
        Format the symbol for Hyperliquid API.
        
        Args:
            symbol: The input symbol (e.g., "ETH", "ETH-PERP", "BTC/USD")
            
        Returns:
            Properly formatted symbol for Hyperliquid API
        """
        # Clean up common formats
        clean_symbol = symbol.upper()
        
        # Remove common suffixes
        if "-PERP" in clean_symbol:
            clean_symbol = clean_symbol.replace("-PERP", "")
        elif "/USD" in clean_symbol:
            clean_symbol = clean_symbol.replace("/USD", "")
        elif "USDT" in clean_symbol and not clean_symbol.startswith("USDT"):
            clean_symbol = clean_symbol.replace("USDT", "")
        
        logger.info(f"Formatted symbol {symbol} to {clean_symbol} for Hyperliquid API")
        return clean_symbol 