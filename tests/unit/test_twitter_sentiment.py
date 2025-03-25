"""Unit tests for Twitter Sentiment Analysis tool."""

import unittest
from unittest.mock import patch, MagicMock
import random
import datetime

from src.tools.twitter_sentiment import TwitterSentimentTool


class TestTwitterSentimentTool(unittest.TestCase):
    """Test suite for the Twitter Sentiment Analysis tool."""

    def setUp(self):
        """Set up the test environment."""
        self.tool = TwitterSentimentTool()
        random.seed(42)  # Ensure predictable "random" results
    
    def test_init(self):
        """Test initialization of the tool."""
        self.assertEqual(self.tool.name, "Twitter Sentiment")
        self.assertEqual(self.tool.description, "Analyzes crypto sentiment on Twitter")
    
    def test_get_sentiment_label(self):
        """Test the sentiment label classification with all categories."""
        # Test very positive sentiment
        self.assertEqual(self.tool._get_sentiment_label(0.7), "Very Positive")
        self.assertEqual(self.tool._get_sentiment_label(0.5), "Very Positive")
        
        # Test positive sentiment
        self.assertEqual(self.tool._get_sentiment_label(0.3), "Positive")
        self.assertEqual(self.tool._get_sentiment_label(0.1), "Positive")
        
        # Test neutral sentiment
        self.assertEqual(self.tool._get_sentiment_label(0.05), "Neutral")
        self.assertEqual(self.tool._get_sentiment_label(0.0), "Neutral")
        self.assertEqual(self.tool._get_sentiment_label(-0.05), "Neutral")
        
        # Test negative sentiment
        self.assertEqual(self.tool._get_sentiment_label(-0.3), "Negative")
        self.assertEqual(self.tool._get_sentiment_label(-0.1), "Negative")
        
        # Test very negative sentiment
        self.assertEqual(self.tool._get_sentiment_label(-0.7), "Very Negative")
        self.assertEqual(self.tool._get_sentiment_label(-0.5), "Very Negative")
    
    def test_generate_realistic_sentiment(self):
        """Test the generation of synthetic sentiment data."""
        result = self.tool._generate_realistic_sentiment("ETH")
        
        # Check that all required fields are present
        self.assertIn("symbol", result)
        self.assertIn("average_sentiment", result)
        self.assertIn("sentiment_label", result)
        self.assertIn("tweet_count", result)
        self.assertIn("positive_percentage", result)
        self.assertIn("negative_percentage", result)
        self.assertIn("neutral_percentage", result)
        self.assertIn("sample_tweets", result)
        
        # Check that the symbol is correctly set
        self.assertEqual(result["symbol"], "ETH")
        
        # Check that sentiment is in the expected range
        self.assertTrue(0.5 <= result["average_sentiment"] <= 0.9)
        
        # Check that percentages sum to 1
        self.assertAlmostEqual(
            result["positive_percentage"] + 
            result["negative_percentage"] + 
            result["neutral_percentage"], 
            1.0, 
            places=5
        )
        
        # Check that sample tweets are provided
        self.assertEqual(len(result["sample_tweets"]), 5)
        
        # Check that all tweet objects have the required structure
        for tweet in result["sample_tweets"]:
            self.assertIn("text", tweet)
            self.assertIn("sentiment", tweet)
            self.assertTrue(isinstance(tweet["text"], str))
            self.assertTrue(isinstance(tweet["sentiment"], float))
    
    def test_run(self):
        """Test the main run method."""
        with patch.object(self.tool, '_generate_realistic_sentiment') as mock_generate:
            mock_generate.return_value = {
                "symbol": "BTC",
                "average_sentiment": 0.6,
                "sentiment_label": "Positive",
                "tweet_count": 100,
                "positive_percentage": 0.7,
                "negative_percentage": 0.1,
                "neutral_percentage": 0.2,
                "sample_tweets": [{"text": "Test", "sentiment": 0.5}]
            }
            
            result = self.tool.run("BTC", 100)
            
            # Verify mock was called with correct parameters
            mock_generate.assert_called_once_with("BTC")
            
            # Check result matches expected output
            self.assertEqual(result["symbol"], "BTC")
            self.assertEqual(result["average_sentiment"], 0.6)
            self.assertEqual(result["sentiment_label"], "Positive")

    def test_get_sentiment_label_all_ranges(self):
        """Test sentiment label across full range of values."""
        # Test boundary cases and random values across the entire range
        test_cases = [
            (1.0, "Very Positive"),
            (0.75, "Very Positive"),
            (0.5, "Very Positive"),
            (0.3, "Positive"),
            (0.1, "Positive"),
            (0.05, "Neutral"),
            (0.0, "Neutral"),
            (-0.05, "Neutral"),
            (-0.1, "Negative"),
            (-0.3, "Negative"),
            (-0.5, "Very Negative"),
            (-0.75, "Very Negative"),
            (-1.0, "Very Negative")
        ]
        
        for score, expected_label in test_cases:
            with self.subTest(score=score):
                self.assertEqual(
                    self.tool._get_sentiment_label(score),
                    expected_label,
                    f"Failed for score {score}, expected {expected_label}"
                )


if __name__ == "__main__":
    unittest.main() 