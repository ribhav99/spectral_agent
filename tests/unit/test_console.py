import unittest
from unittest.mock import patch, MagicMock
import io
import sys
from src.utils.console import display_results

class TestConsole(unittest.TestCase):
    """Test console utility functions."""
    
    def setUp(self):
        """Set up for tests."""
        # Redirect stdout to capture print statements
        self.held_output = io.StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.held_output
    
    def tearDown(self):
        """Clean up after tests."""
        # Restore stdout
        sys.stdout = self.original_stdout
    
    def get_output(self):
        """Get captured output."""
        return self.held_output.getvalue()
    
    def test_display_results_empty(self):
        """Test display_results with empty results."""
        display_results({})
        output = self.get_output()
        self.assertIn("No results to display", output)
    
    def test_display_results_none(self):
        """Test display_results with None."""
        display_results(None)
        output = self.get_output()
        self.assertIn("No results to display", output)
    
    def test_display_results_error(self):
        """Test display_results with error status."""
        results = {
            "status": "error",
            "message": "Test error message",
            "symbol": "BTC",
            "timestamp": 1234567890
        }
        display_results(results)
        output = self.get_output()
        self.assertIn("Error: Test error message", output)
        self.assertIn("Symbol: BTC", output)
        self.assertIn("Timestamp: 1234567890", output)
    
    def test_display_results_message(self):
        """Test display_results with a simple message."""
        results = {
            "message": "Test message"
        }
        display_results(results)
        output = self.get_output()
        self.assertIn("Message: Test message", output)
    
    def test_display_results_decision_neutral(self):
        """Test display_results with a neutral trading decision."""
        results = {
            "decision": "NEUTRAL",
            "symbol": "BTC",
            "confidence": 0.75,
            "reasoning": "Market is sideways",
            "action": "No trade executed"
        }
        display_results(results)
        output = self.get_output()
        self.assertIn("Trading Decision:", output)
        self.assertIn("Symbol: BTC", output)
        self.assertIn("Decision: NEUTRAL", output)
        self.assertIn("Confidence: 75.0%", output)
        self.assertIn("Reasoning: Market is sideways", output)
        self.assertIn("Action: No trade executed", output)
    
    def test_display_results_decision_long(self):
        """Test display_results with a LONG trading decision."""
        results = {
            "decision": "LONG",
            "symbol": "ETH",
            "confidence": 0.9,
            "reasoning": "Strong uptrend",
            "position_size": 0.25,
            "stop_loss": 0.05,
            "take_profit": 0.15,
            "market_data": {
                "current_price": 3000.0,
                "24h_change_percent": 5.5,
                "indicators": {
                    "rsi_14": 65.5
                }
            },
            "sentiment_data": {
                "average_sentiment": 0.78,
                "sentiment_label": "Very Positive",
                "tweet_count": 120
            },
            "trading_amount": 500.0
        }
        display_results(results)
        output = self.get_output()
        
        # Check decision information
        self.assertIn("Trading Decision:", output)
        self.assertIn("Symbol: ETH", output)
        self.assertIn("Decision: LONG", output)
        self.assertIn("Confidence: 90.0%", output)
        self.assertIn("Reasoning: Strong uptrend", output)
        
        # Check position details
        self.assertIn("Position Size: 25.0%", output)
        self.assertIn("Stop Loss: 5.0%", output)
        self.assertIn("Take Profit: 15.0%", output)
        
        # Check market data
        self.assertIn("Market Data Used:", output)
        self.assertIn("Current Price: $3000.00", output)
        self.assertIn("24h Change: 5.50%", output)
        self.assertIn("RSI: 65.50", output)
        
        # Check sentiment data
        self.assertIn("Sentiment Data Used:", output)
        self.assertIn("Average Sentiment: 0.78", output)
        self.assertIn("Sentiment Label: Very Positive", output)
        self.assertIn("Tweet Count: 120", output)
        
        # Check trading amount
        self.assertIn("Trading Amount: $500.00", output)
    
    def test_display_results_execution_result(self):
        """Test display_results with execution result."""
        results = {
            "symbol": "BTC",
            "direction": "LONG",
            "entry_price": 50000.0,
            "position_size_usd": 1000.0,
            "stop_loss_price": 48000.0,
            "take_profit_price": 55000.0,
            "execution_result": {
                "status": "success",
                "is_dry_run": True
            }
        }
        display_results(results)
        output = self.get_output()
        
        # Check execution information
        self.assertIn("Trade Execution:", output)
        self.assertIn("Symbol: BTC", output)
        self.assertIn("Direction: LONG", output)
        self.assertIn("Entry Price: $50000.00", output)
        self.assertIn("Position Size: $1000.00", output)
        self.assertIn("Stop Loss Price: $48000.00", output)
        self.assertIn("Take Profit Price: $55000.00", output)
        
        # Check execution status
        self.assertIn("Execution Status: success", output)
        self.assertIn("This was a dry run", output)
    
    def test_display_results_execution_error(self):
        """Test display_results with execution error."""
        results = {
            "symbol": "BTC",
            "direction": "LONG",
            "execution_result": {
                "status": "error",
                "message": "Insufficient balance"
            }
        }
        display_results(results)
        output = self.get_output()
        
        self.assertIn("Trade Execution:", output)
        self.assertIn("Execution Status: error", output)
        self.assertIn("Error: Insufficient balance", output)
    
    def test_display_results_market_data(self):
        """Test display_results with market data."""
        results = {
            "current_price": 50000.0,
            "24h_change_percent": -2.5,
            "indicators": {
                "rsi_14": 35.5,
                "macd": -0.0025,
                "bb_middle": 51000.0,
                "trend": "down",
                "volatility": "high"
            },
            "is_synthetic": True
        }
        display_results(results)
        output = self.get_output()
        
        # Check market data
        self.assertIn("Market Data:", output)
        self.assertIn("Current Price: $50000.00", output)
        self.assertIn("24h Change: -2.50%", output)
        
        # Check indicators
        self.assertIn("RSI: 35.50", output)
        self.assertIn("MACD: -0.0025", output)
        self.assertIn("Bollinger Middle: $51000.00", output)
        self.assertIn("Trend: down", output)
        self.assertIn("Volatility: high", output)
        
        # Check synthetic data note
        self.assertIn("Note: Using synthetic market data", output)
    
    def test_display_results_none_values(self):
        """Test display_results with None values."""
        results = {
            "current_price": None,
            "24h_change_percent": None,
            "indicators": {
                "rsi_14": None
            }
        }
        display_results(results)
        output = self.get_output()
        
        self.assertIn("Current Price: Not available", output)
        self.assertIn("24h Change: Not available", output)
        self.assertIn("RSI: Not available", output)
    
    def test_display_results_sentiment_data(self):
        """Test display_results with sentiment data."""
        results = {
            "average_sentiment": 0.65,
            "sentiment_label": "Positive",
            "positive_percentage": 0.75,
            "negative_percentage": 0.15,
            "tweet_count": 150
        }
        display_results(results)
        output = self.get_output()
        
        self.assertIn("Sentiment Analysis:", output)
        self.assertIn("Average Sentiment: 0.65", output)
        self.assertIn("Sentiment Label: Positive", output)
        self.assertIn("Positive %: 75.0%", output)
        self.assertIn("Negative %: 15.0%", output)
        self.assertIn("Tweet Count: 150", output)
    
    def test_display_results_tool_results(self):
        """Test display_results with tool results."""
        results = {
            "tool_results": {
                "market_data": {
                    "current_price": 50000.0,
                    "is_synthetic": True
                },
                "sentiment_analysis": {
                    "average_sentiment": 0.65,
                    "complex_data": {"extremely": {"nested": {"structure": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 100}}}
                },
                "list_tool": [1, 2, 3, 4, 5]
            }
        }
        display_results(results)
        output = self.get_output()
        
        self.assertIn("Tools Used: market_data, sentiment_analysis, list_tool", output)
        self.assertIn("Tool Results:", output)
        self.assertIn("market_data:", output)
        self.assertIn("current_price: 50000.0", output)
        self.assertIn("is_synthetic: True", output)
        self.assertIn("sentiment_analysis:", output)
        self.assertIn("average_sentiment: 0.65", output)
        self.assertIn("complex_data: [Complex data structure]", output)
    
    @patch('builtins.input', side_effect=["trade BTC", "ETH", "200", "n"])
    def test_get_user_input(self, mock_input):
        """Test get_user_input function."""
        # Import here to avoid stdout redirection issues
        from src.utils.console import get_user_input
        
        result = get_user_input()
        self.assertEqual(result["prompt"], "trade BTC")
        self.assertEqual(result["symbol"], "ETH")
        self.assertEqual(result["amount"], 200.0)
        self.assertEqual(result["dry_run"], False)
    
    @patch('builtins.input', side_effect=["test prompt", "", "", ""])
    def test_get_user_input_defaults(self, mock_input):
        """Test get_user_input function with defaults."""
        from src.utils.console import get_user_input
        
        result = get_user_input()
        self.assertEqual(result["prompt"], "test prompt")
        self.assertEqual(result["symbol"], "BTC")  # Default
        self.assertEqual(result["amount"], 100.0)  # Default
        self.assertEqual(result["dry_run"], True)  # Default
    
    @patch('builtins.input', side_effect=["test prompt", "ETH", "invalid", "n"])
    def test_get_user_input_invalid_amount(self, mock_input):
        """Test get_user_input with invalid amount."""
        from src.utils.console import get_user_input
        
        result = get_user_input()
        self.assertEqual(result["amount"], 100.0)  # Default when invalid


if __name__ == "__main__":
    unittest.main() 