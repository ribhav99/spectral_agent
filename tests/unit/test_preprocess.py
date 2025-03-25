import unittest
from src.utils.preprocess import clean_text, normalize_market_data, format_for_llm_input

class TestPreprocess(unittest.TestCase):
    """Test preprocess utility functions."""
    
    def test_clean_text_normal(self):
        """Test clean_text with normal text."""
        text = "Hello world! This is a test. #crypto"
        result = clean_text(text)
        self.assertEqual(result, "hello world this is a test crypto")
    
    def test_clean_text_with_urls(self):
        """Test clean_text with URLs."""
        text = "Check out https://example.com and http://test.org for more info!"
        result = clean_text(text)
        self.assertEqual(result, "check out  and  for more info")
    
    def test_clean_text_with_numbers(self):
        """Test clean_text with numbers."""
        text = "BTC is at $50,000 today!"
        result = clean_text(text)
        self.assertEqual(result, "btc is at 50000 today")
    
    def test_clean_text_empty(self):
        """Test clean_text with empty text."""
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text(None), "")
    
    def test_clean_text_special_chars(self):
        """Test clean_text with special characters."""
        text = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = clean_text(text)
        self.assertEqual(result, "_")
    
    def test_normalize_market_data_complete(self):
        """Test normalize_market_data with complete data."""
        data = {
            "price": "50000.5",
            "ohlc": ["49000.1", "51000.2", "48500.3", "50000.4"]
        }
        result = normalize_market_data(data)
        
        self.assertEqual(result["current_price"], 50000.5)
        self.assertEqual(result["open"], 49000.1)
        self.assertEqual(result["high"], 51000.2)
        self.assertEqual(result["low"], 48500.3)
        self.assertEqual(result["close"], 50000.4)
        
        # Check volatility calculation
        expected_volatility = (51000.2 - 48500.3) / 48500.3
        self.assertAlmostEqual(result["volatility"], expected_volatility)
    
    def test_normalize_market_data_partial(self):
        """Test normalize_market_data with partial data."""
        # Only price, no OHLC
        data1 = {"price": "50000.5"}
        result1 = normalize_market_data(data1)
        self.assertEqual(result1["current_price"], 50000.5)
        self.assertNotIn("open", result1)
        self.assertNotIn("volatility", result1)
        
        # Only OHLC, no price
        data2 = {"ohlc": ["49000.1", "51000.2", "48500.3", "50000.4"]}
        result2 = normalize_market_data(data2)
        self.assertNotIn("current_price", result2)
        self.assertEqual(result2["open"], 49000.1)
        
        # Partial OHLC
        data3 = {"ohlc": ["49000.1", "51000.2"]}
        result3 = normalize_market_data(data3)
        self.assertEqual(result3["open"], 49000.1)
        self.assertEqual(result3["high"], 51000.2)
        self.assertIsNone(result3["low"])
        self.assertIsNone(result3["close"])
        self.assertNotIn("volatility", result3)
        
        # Empty OHLC
        data4 = {"ohlc": []}
        result4 = normalize_market_data(data4)
        self.assertIsNone(result4["open"])
    
    def test_normalize_market_data_empty(self):
        """Test normalize_market_data with empty data."""
        result = normalize_market_data({})
        self.assertEqual(result, {})
    
    def test_format_for_llm_input_simple(self):
        """Test format_for_llm_input with simple data."""
        data = {
            "symbol": "BTC",
            "price": 50000.5,
            "change": -2.5
        }
        result = format_for_llm_input(data)
        expected = "Symbol: BTC\nPrice: 50000.5\nChange: -2.5"
        self.assertEqual(result, expected)
    
    def test_format_for_llm_input_nested(self):
        """Test format_for_llm_input with nested data."""
        data = {
            "symbol": "BTC",
            "price": 50000.5,
            "indicators": {
                "rsi": 45.6,
                "macd": -0.0025
            }
        }
        result = format_for_llm_input(data)
        self.assertIn("Symbol: BTC", result)
        self.assertIn("Price: 50000.5", result)
        self.assertIn("Rsi: 45.6", result)
        self.assertIn("Macd: -0.0025", result)
    
    def test_format_for_llm_input_with_list(self):
        """Test format_for_llm_input with list data."""
        data = {
            "symbol": "BTC",
            "prices": [50000.5, 49800.3, 51200.8]
        }
        result = format_for_llm_input(data)
        self.assertIn("Symbol: BTC", result)
        self.assertIn("Prices: 50000.5, 49800.3, 51200.8", result)
    
    def test_format_for_llm_input_with_float_formatting(self):
        """Test format_for_llm_input handles float formatting correctly."""
        data = {
            "precise_value": 123.456789,
            "whole_number": 123.0,
            "zero": 0.0
        }
        result = format_for_llm_input(data)
        self.assertIn("Precise Value: 123.456789", result)
        self.assertIn("Whole Number: 123", result)
        self.assertIn("Zero: 0", result)
    
    def test_format_for_llm_input_empty(self):
        """Test format_for_llm_input with empty data."""
        self.assertEqual(format_for_llm_input({}), "")


if __name__ == "__main__":
    unittest.main() 