"""Trading execution tool for executing trades on Hyperliquid."""

import time
import json
from typing import Dict, List, Any, Optional
import base64
import requests
from eth_account import Account
from eth_account.messages import encode_defunct
import hmac
import hashlib

from ..utils.logger import setup_logger
from .. import config

logger = setup_logger("trading_execution_tool")

class TradingExecutionTool:
    """Tool for executing trades on Hyperliquid based on decisions."""
    
    def __init__(self):
        """Initialize the trading execution tool."""
        self.name = "Trading Execution"
        self.description = "Executes trades on Hyperliquid based on decisions"
        
        # Initialize trading connection
        self.base_url = config.HYPERLIQUID_API_TESTNET
        self.private_key = config.HYPERLIQUID_PRIVATE_KEY
        
        # Derive wallet address from private key
        if self.private_key:
            account = Account.from_key(self.private_key)
            self.wallet_address = account.address
            logger.info(f"Initialized trading executor with wallet: {self.wallet_address}")
        else:
            self.wallet_address = None
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
        Execute a trade based on market data and sentiment analysis.
        
        Args:
            symbol: Cryptocurrency symbol to trade
            direction: "LONG" or "SHORT" (takes precedence if provided)
            position_size: Position size as fraction of balance
            stop_loss: Stop loss percentage
            take_profit: Take profit percentage
            amount: Dollar amount available for trading
            market_data: Optional pre-fetched market data
            sentiment_data: Optional sentiment analysis data
            dry_run: If True, simulate the trade without actual execution
            
        Returns:
            Dictionary with trade execution results
        """
        # Validate the amount parameter to ensure it's not been overridden with an incorrect value
        logger.info(f"Trading execution tool called for symbol: {symbol}, amount: ${amount}")
        
        # Check if amount is too large, which might indicate an incorrect value
        if amount > 1000:
            logger.warning(f"Amount ${amount} seems unusually large. This may be an error. Double-check parameter.")
            
        # If direction is explicitly provided, use it
        if direction:
            trade_direction = direction.upper()
            reasoning = "Using explicitly provided direction"
            logger.info(f"Using explicitly provided direction: {trade_direction}")
        else:
            # Make a trading decision based on market data and sentiment
            trade_decision = self._make_trading_decision(symbol, market_data, sentiment_data)
            trade_direction = trade_decision["direction"]
            reasoning = trade_decision["reasoning"]
            
            # If no clear direction, don't trade
            if trade_direction == "NEUTRAL":
                logger.info(f"Decision is NEUTRAL - no trade will be executed")
                return {
                    "symbol": symbol,
                    "decision": "NEUTRAL",
                    "reasoning": reasoning,
                    "action": "No trade executed",
                    "timestamp": int(time.time())
                }
            
        # Create decision dict
        custom_decision = {
            "symbol": symbol,
            "decision": trade_direction,
            "position_size": position_size or config.DEFAULT_POSITION_SIZE,
            "stop_loss": stop_loss or config.DEFAULT_STOP_LOSS_PERCENT,
            "take_profit": take_profit or (config.DEFAULT_STOP_LOSS_PERCENT * 2),
            "confidence": 1.0,  # Default confidence
            "reasoning": reasoning
        }
        
        logger.info(f"Executing trade: {custom_decision['decision']} {symbol} with ${amount}")
        result = self.execute_trade(custom_decision, dry_run=dry_run, amount=amount, market_data=market_data)
        
        # Add sentiment data to the result if provided
        if sentiment_data:
            result["sentiment_data"] = sentiment_data
            
        return result
    
    def execute_trade(self, 
                     decision: Dict[str, Any],
                     dry_run: bool = False,
                     amount: float = 100.0,
                     market_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a trade based on a decision.
        
        Args:
            decision: Trading decision dict containing symbol, direction, etc.
            dry_run: If True, simulate the trade without execution
            amount: Dollar amount available for trading
            market_data: Optional pre-fetched market data
            
        Returns:
            Dictionary with trade execution results
        """
        if not decision:
            logger.error("No decision provided")
            return {"status": "error", "message": "No decision provided"}
        
        symbol = decision.get("symbol", "BTC")
        direction = decision.get("decision", "")
        position_size = decision.get("position_size", config.DEFAULT_POSITION_SIZE)
        stop_loss = decision.get("stop_loss", config.DEFAULT_STOP_LOSS_PERCENT)
        take_profit = decision.get("take_profit", stop_loss * 2)
        
        logger.info(f"Executing {direction} trade for {symbol} with size {position_size}, amount: ${amount}")
        
        # Validate decision
        if direction not in ["LONG", "SHORT"]:
            logger.error(f"Invalid direction: {direction}")
            return {"status": "error", "message": f"Invalid direction: {direction}"}
        
        # Convert direction to side
        side = "b" if direction == "LONG" else "a"
        
        # Check if we already have market data available
        current_price = None
        if market_data and market_data.get("symbol") == symbol and market_data.get("current_price"):
            # Use the price from pre-fetched market data
            current_price = market_data.get("current_price")
            logger.info(f"Using pre-fetched price for {symbol}: ${current_price}")
        else:
            # If no pre-fetched data, attempt to get market price directly
            logger.info(f"No pre-fetched price found, fetching market price for {symbol}")
            current_price = self._get_market_price(symbol)
        
        # Ensure we have a valid price
        if not current_price:
            return {"status": "error", "message": f"Could not get price for {symbol}"}
        
        # Use the specified amount instead of account balance
        usd_position = amount * position_size
        
        # Calculate position size in crypto units
        size = usd_position / current_price
        
        # Calculate stop loss and take profit prices
        if direction == "LONG":
            stop_loss_price = current_price * (1 - stop_loss)
            take_profit_price = current_price * (1 + take_profit)
        else:
            stop_loss_price = current_price * (1 + stop_loss)
            take_profit_price = current_price * (1 - take_profit)
        
        # Execute trade
        if dry_run:
            logger.info(f"DRY RUN: Would execute {direction} for {symbol} at {current_price} with size {size}, amount: ${usd_position}")
            execution_result = {
                "status": "success",
                "message": "Dry run completed",
                "is_dry_run": True
            }
        else:
            if not self.private_key:
                logger.warning("No private key available, running in simulation mode")
                execution_result = {
                    "status": "success",
                    "message": "Simulated execution (no private key)",
                    "is_simulation": True
                }
            else:
                # Execute the order on Hyperliquid
                execution_result = self._place_order(symbol, side, size)
                
                # If successful, place stop loss and take profit orders
                if execution_result.get("status") == "success":
                    logger.info("Order executed successfully, placing stop loss and take profit orders")
                    
                    # Place stop loss
                    sl_size = size  # Same size as entry position
                    sl_side = "a" if direction == "LONG" else "b"  # Opposite of entry position
                    sl_result = self._place_order(symbol, sl_side, sl_size, 
                                                  order_type="limit", 
                                                  price=stop_loss_price,
                                                  reduce_only=True)
                    
                    # Place take profit
                    tp_size = size  # Same size as entry position
                    tp_side = "a" if direction == "LONG" else "b"  # Opposite of entry position
                    tp_result = self._place_order(symbol, tp_side, sl_size, 
                                                  order_type="limit", 
                                                  price=take_profit_price,
                                                  reduce_only=True)
                    
                    # Add stop loss and take profit info to result
                    execution_result["stop_loss"] = sl_result
                    execution_result["take_profit"] = tp_result
        
        # Prepare the complete result
        result = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": current_price,
            "position_size_usd": usd_position,
            "position_size_units": size,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "execution_result": execution_result,
            "timestamp": int(time.time()),
            "trading_amount": amount
        }
        
        # Include market data if provided
        if market_data:
            result["market_data"] = market_data
            
        return result
    
    def _get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol."""
        try:
            logger.info(f"Fetching market price for {symbol} from {self.base_url}/info")
            endpoint = f"{self.base_url}/info"
            response = requests.get(endpoint)
            
            if response.status_code == 200:
                data = response.json()
                
                # Log the response structure for debugging
                logger.debug(f"API response structure: {list(data.keys())}")
                
                # Check if markets data exists
                if "markets" not in data:
                    logger.error(f"No 'markets' field in API response: {data}")
                    # Return a sample price for testing
                    sample_price = {
                        "BTC": 35000,
                        "ETH": 2000,
                        "SOL": 100
                    }.get(symbol, 100)
                    logger.info(f"Using sample price for {symbol}: ${sample_price}")
                    return sample_price
                
                # Find the matching asset in the response
                symbols_in_response = [market.get("symbol") for market in data.get("markets", [])]
                logger.debug(f"Available symbols in API response: {symbols_in_response}")
                
                for market in data.get("markets", []):
                    if market.get("symbol") == symbol:
                        price = float(market.get("mark_price", 0))
                        logger.info(f"Found market price for {symbol}: ${price}")
                        return price
                
                logger.error(f"Symbol {symbol} not found in markets list. Available symbols: {symbols_in_response}")
            else:
                logger.error(f"API request failed with status code {response.status_code}: {response.text}")
            
            # Return a sample price as fallback
            sample_price = {
                "BTC": 35000,
                "ETH": 2000,
                "SOL": 100
            }.get(symbol, 100)
            logger.info(f"Using sample price for {symbol}: ${sample_price}")
            return sample_price
            
        except Exception as e:
            logger.error(f"Exception getting market price for {symbol}: {str(e)}", exc_info=True)
            # Return a sample price as fallback
            sample_price = {
                "BTC": 35000,
                "ETH": 2000,
                "SOL": 100
            }.get(symbol, 100)
            logger.info(f"Using sample price for {symbol} after exception: ${sample_price}")
            return sample_price
    
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
    
    def _place_order(self, 
                    symbol: str, 
                    side: str, 
                    size: float, 
                    order_type: str = "market",
                    price: Optional[float] = None,
                    reduce_only: bool = False) -> Dict[str, Any]:
        """
        Place an order on Hyperliquid.
        
        Args:
            symbol: Cryptocurrency symbol
            side: 'b' for buy/long, 'a' for sell/short
            size: Position size in crypto units
            order_type: 'market', 'limit', or 'stop'
            price: Limit price (required for limit and stop orders)
            reduce_only: Whether the order should only reduce an existing position
            
        Returns:
            Dictionary with order execution result
        """
        try:
            if not self.private_key:
                return {
                    "status": "success",
                    "message": "Simulated order (no private key)",
                    "is_simulation": True
                }
            
            # Prepare order data
            order_data = {
                "symbol": symbol,
                "side": side,
                "size": str(size),
                "order_type": order_type
            }
            
            if price:
                order_data["limit_px"] = str(price)
            
            if reduce_only:
                order_data["reduce_only"] = True
            
            # Sign the request
            signature = self._sign_request(order_data)
            
            # Send request to API
            endpoint = f"{self.base_url}/order"
            headers = {
                "Content-Type": "application/json",
                "X-Signature": signature
            }
            
            response = requests.post(endpoint, json=order_data, headers=headers)
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "message": "Order executed",
                    "order_id": response.json().get("order_id"),
                    "response": response.json()
                }
            else:
                logger.error(f"Order execution failed: {response.text}")
                return {
                    "status": "error",
                    "message": f"Order execution failed: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return {
                "status": "error",
                "message": f"Error placing order: {str(e)}"
            }
    
    def _sign_request(self, data: Dict[str, Any]) -> str:
        """
        Sign an API request using the private key.
        
        Args:
            data: Request data to sign
            
        Returns:
            Hex signature string
        """
        try:
            if not self.private_key:
                return ""
            
            # Convert data to JSON string
            message = json.dumps(data, separators=(',', ':'))
            
            # Create message hash
            message_hash = encode_defunct(text=message)
            
            # Sign the message
            signed_message = Account.sign_message(message_hash, private_key=self.private_key)
            
            # Return the signature
            return signed_message.signature.hex()
            
        except Exception as e:
            logger.error(f"Error signing request: {str(e)}")
            return ""
    
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