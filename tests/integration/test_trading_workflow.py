"""Integration tests for the complete trading workflow."""

import unittest
from unittest.mock import patch, MagicMock
import time
import os
import sys
import json
from typing import Dict, Any

from src.tools.market_data import MarketDataTool
from src.tools.twitter_sentiment import TwitterSentimentTool
from src.tools.trading_execution import TradingExecutionTool


class TestTradingWorkflow(unittest.TestCase):
    """Test suite for the complete trading workflow."""

    def setUp(self):
        """Set up the test environment."""
        self.market_tool = MarketDataTool()
        self.sentiment_tool = TwitterSentimentTool()
        self.trading_tool = TradingExecutionTool()
        
        # Mock the exchange initialization
        self.trading_tool.exchange = MagicMock()
        self.trading_tool.info = MagicMock()
        self.trading_tool.wallet_address = "0x1234567890abcdef"
        self.trading_tool.base_url = "https://api.hyperliquid.xyz"
    
    @patch('src.tools.twitter_sentiment.TwitterSentimentTool._generate_realistic_sentiment')
    @patch('src.tools.market_data.MarketDataTool._generate_realistic_market_data')
    @patch('src.tools.trading_execution.TradingExecutionTool._place_order')
    def test_positive_sentiment_workflow(self, mock_place_order, mock_market_data, mock_sentiment):
        """Test the workflow with positive sentiment leading to a LONG trade."""
        # Setup mock for sentiment data with positive result
        mock_sentiment.return_value = {
            "symbol": "ETH",
            "average_sentiment": 0.7,
            "sentiment_label": "Very Positive",
            "tweet_count": 150,
            "positive_percentage": 0.75,
            "negative_percentage": 0.05,
            "neutral_percentage": 0.2,
            "sample_tweets": [
                {"text": "ETH looking super bullish today!", "sentiment": 0.8}
            ]
        }
        
        # Setup mock for market data with bullish indicators
        mock_market_data.return_value = {
            "symbol": "ETH",
            "current_price": 3000.0,
            "24h_change_percent": 2.5,
            "24h_volume": 15000000000.0,
            "funding_rate": 0.0001,
            "open_interest": 5000000000.0,
            "timeframe": "1h",
            "indicators": {
                "rsi_14": 60.0,
                "sma_20": 2900.0,
                "ema_12": 2950.0,
                "ema_26": 2850.0,
                "macd": 100.0,
                "macd_signal": 80.0,
                "macd_hist": 20.0,
                "bb_upper": 3100.0,
                "bb_middle": 2900.0,
                "bb_lower": 2700.0
            },
            "timestamp": int(time.time()),
            "is_synthetic": True
        }
        
        # Setup mock for successful trade execution
        mock_place_order.return_value = {
            "status": "ok",
            "response": {
                "type": "success",
                "data": {
                    "statuses": [{
                        "filled": {
                            "oid": 12345,
                            "totalSz": 0.033,
                            "avgPx": 3000.0
                        }
                    }]
                }
            }
        }
        
        # 1. Get sentiment data
        sentiment_data = self.sentiment_tool.run("ETH")
        
        # 2. Get market data
        market_data = self.market_tool.run("ETH", "1h")
        
        # 3. Execute trade based on sentiment and market data
        trade_result = self.trading_tool.run(
            symbol="ETH",
            amount=100.0,
            market_data=market_data,
            sentiment_data=sentiment_data,
            dry_run=True
        )
        
        # Verify each step of the workflow
        
        # Verify sentiment data was correctly processed
        self.assertEqual(sentiment_data["symbol"], "ETH")
        self.assertEqual(sentiment_data["sentiment_label"], "Very Positive")
        
        # Verify market data was correctly processed
        self.assertEqual(market_data["symbol"], "ETH")
        
        # Verify trading decision led to LONG position due to positive sentiment
        self.assertEqual(trade_result["direction"], "LONG")
        self.assertEqual(trade_result["symbol"], "ETH")
        
        # Verify the trade execution
        self.assertEqual(trade_result["status"], "executed")
    
    @patch('src.tools.twitter_sentiment.TwitterSentimentTool._generate_realistic_sentiment')
    @patch('src.tools.market_data.MarketDataTool._generate_realistic_market_data')
    @patch('src.tools.trading_execution.TradingExecutionTool._place_order')
    def test_negative_sentiment_workflow(self, mock_place_order, mock_market_data, mock_sentiment):
        """Test the workflow with negative sentiment leading to a SHORT trade."""
        # Setup mock for sentiment data with negative result
        mock_sentiment.return_value = {
            "symbol": "ETH",
            "average_sentiment": -0.6,
            "sentiment_label": "Negative",
            "tweet_count": 120,
            "positive_percentage": 0.15,
            "negative_percentage": 0.7,
            "neutral_percentage": 0.15,
            "sample_tweets": [
                {"text": "ETH looking weak today, selling my bags", "sentiment": -0.7}
            ]
        }
        
        # Setup mock for market data with bearish indicators
        mock_market_data.return_value = {
            "symbol": "ETH",
            "current_price": 3000.0,
            "24h_change_percent": -3.5,
            "24h_volume": 18000000000.0,
            "funding_rate": -0.0002,
            "open_interest": 4500000000.0,
            "timeframe": "1h",
            "indicators": {
                "rsi_14": 30.0,
                "sma_20": 3100.0,
                "ema_12": 3050.0,
                "ema_26": 3150.0,
                "macd": -80.0,
                "macd_signal": -60.0,
                "macd_hist": -20.0,
                "bb_upper": 3300.0,
                "bb_middle": 3100.0,
                "bb_lower": 2900.0
            },
            "timestamp": int(time.time()),
            "is_synthetic": True
        }
        
        # Setup mock for successful trade execution
        mock_place_order.return_value = {
            "status": "ok",
            "response": {
                "type": "success",
                "data": {
                    "statuses": [{
                        "filled": {
                            "oid": 12346,
                            "totalSz": 0.033,
                            "avgPx": 3000.0
                        }
                    }]
                }
            }
        }
        
        # Execute the workflow
        sentiment_data = self.sentiment_tool.run("ETH")
        market_data = self.market_tool.run("ETH", "1h")
        trade_result = self.trading_tool.run(
            symbol="ETH",
            amount=100.0,
            market_data=market_data,
            sentiment_data=sentiment_data,
            dry_run=True
        )
        
        # Verify sentiment data
        self.assertEqual(sentiment_data["sentiment_label"], "Negative")
        
        # Verify market data
        self.assertEqual(market_data["symbol"], "ETH")
        
        # Verify trading decision led to SHORT position due to negative sentiment
        self.assertEqual(trade_result["direction"], "SHORT")
        
        # Verify the trade execution
        self.assertEqual(trade_result["status"], "executed")
    
    @patch('src.tools.twitter_sentiment.TwitterSentimentTool._generate_realistic_sentiment')
    @patch('src.tools.market_data.MarketDataTool._generate_realistic_market_data')
    @patch('src.tools.trading_execution.TradingExecutionTool._place_order')
    def test_neutral_sentiment_workflow(self, mock_place_order, mock_market_data, mock_sentiment):
        """Test the workflow with neutral sentiment leading to no trade."""
        # Setup mock for sentiment data with neutral result
        mock_sentiment.return_value = {
            "symbol": "ETH",
            "average_sentiment": 0.1,
            "sentiment_label": "Neutral",
            "tweet_count": 100,
            "positive_percentage": 0.33,
            "negative_percentage": 0.33,
            "neutral_percentage": 0.34,
            "sample_tweets": [
                {"text": "ETH moving sideways, waiting for a breakout", "sentiment": 0.1}
            ]
        }
        
        # Setup mock for market data with neutral indicators
        mock_market_data.return_value = {
            "symbol": "ETH",
            "current_price": 3000.0,
            "24h_change_percent": 0.5,
            "24h_volume": 10000000000.0,
            "funding_rate": 0.0001,
            "open_interest": 4000000000.0,
            "timeframe": "1h",
            "indicators": {
                "rsi_14": 50.0,
                "sma_20": 3000.0,
                "ema_12": 3000.0,
                "ema_26": 3000.0,
                "macd": 5.0,
                "macd_signal": 5.0,
                "macd_hist": 0.0,
                "bb_upper": 3100.0,
                "bb_middle": 3000.0,
                "bb_lower": 2900.0
            },
            "timestamp": int(time.time()),
            "is_synthetic": True
        }
        
        # Force the trading decision to be NEUTRAL
        with patch.object(self.trading_tool, '_make_trading_decision') as mock_decision:
            mock_decision.return_value = {
                "direction": "NEUTRAL",
                "confidence": 0.5,
                "reasoning": "Neutral market conditions and sentiment"
            }
            
            # Execute the workflow
            sentiment_data = self.sentiment_tool.run("ETH")
            market_data = self.market_tool.run("ETH", "1h")
            trade_result = self.trading_tool.run(
                symbol="ETH",
                amount=100.0,
                market_data=market_data,
                sentiment_data=sentiment_data,
                dry_run=True
            )
            
            # Verify trading decision led to no trade
            self.assertEqual(trade_result["direction"], "NEUTRAL")
            self.assertEqual(trade_result["status"], "not_executed")
            
            # Verify no order was placed
            mock_place_order.assert_not_called()


if __name__ == "__main__":
    unittest.main() 