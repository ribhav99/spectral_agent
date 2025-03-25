"""Unit tests for Twitter Sentiment Analysis tool."""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import random
import subprocess
import os
import datetime
from textblob import TextBlob
import importlib
import ssl
import time

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

    def test_scrape_tweets_subprocess_error(self):
        """Test handling errors in the subprocess method to scrape tweets."""
        with patch('subprocess.Popen') as mock_popen:
            # Simulate a subprocess error
            mock_popen.side_effect = Exception("Subprocess error")
            
            # Should return empty list when subprocess fails
            result = self.tool._scrape_tweets("BTC", 10)
            self.assertEqual(result, [])
    
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

    def test_fix_mac_certificates_darwin(self):
        """Test certificate fix for macOS."""
        # Mock platform.system to return 'Darwin' (macOS)
        with patch('platform.system', return_value='Darwin'):
            # Create a fake certifi module
            mock_certifi = MagicMock()
            mock_certifi.where.return_value = '/fake/path/to/cacert.pem'
            
            # Mock the import of certifi
            with patch.dict('sys.modules', {'certifi': mock_certifi}):
                # Store the original env var
                original_ssl_cert_file = os.environ.get('SSL_CERT_FILE')
                
                try:
                    # Call the method
                    self.tool._fix_mac_certificates()
                    
                    # Check if the environment variable was set correctly
                    self.assertEqual(os.environ.get('SSL_CERT_FILE'), '/fake/path/to/cacert.pem')
                    # Verify where() was called
                    mock_certifi.where.assert_called_once()
                finally:
                    # Restore the original environment
                    if original_ssl_cert_file:
                        os.environ['SSL_CERT_FILE'] = original_ssl_cert_file
                    elif 'SSL_CERT_FILE' in os.environ:
                        del os.environ['SSL_CERT_FILE']
    
    def test_fix_mac_certificates_darwin_fallback(self):
        """Test certificate fix for macOS with fallback path."""
        # Mock platform.system to return 'Darwin' (macOS)
        with patch('platform.system', return_value='Darwin'):
            # Mock ImportError for certifi import
            with patch.dict('sys.modules', {'certifi': None}):
                with patch('builtins.__import__', side_effect=lambda name, *args: 
                           __import__(name, *args) if name != 'certifi' else exec('raise ImportError("No module named \'certifi\'")')):
                    
                    # Store the original env var
                    original_ssl_cert_file = os.environ.get('SSL_CERT_FILE')
                    
                    try:
                        # Call the method
                        self.tool._fix_mac_certificates()
                        
                        # Check if the environment variable was set to the fallback path
                        self.assertEqual(os.environ.get('SSL_CERT_FILE'), '/etc/ssl/cert.pem')
                    finally:
                        # Restore the original environment
                        if original_ssl_cert_file:
                            os.environ['SSL_CERT_FILE'] = original_ssl_cert_file
                        elif 'SSL_CERT_FILE' in os.environ:
                            del os.environ['SSL_CERT_FILE']

    def test_fix_mac_certificates_non_darwin(self):
        """Test certificate fix for non-macOS platforms."""
        # Mock platform.system to return 'Linux'
        with patch('platform.system', return_value='Linux'):
            # Store the original env var
            original_ssl_cert_file = os.environ.get('SSL_CERT_FILE')
            
            try:
                # Call the method
                self.tool._fix_mac_certificates()
                
                # Verify the environment variable was not modified for Linux
                self.assertEqual(os.environ.get('SSL_CERT_FILE'), original_ssl_cert_file)
            finally:
                # Restore the original environment if it existed
                if original_ssl_cert_file:
                    os.environ['SSL_CERT_FILE'] = original_ssl_cert_file
                elif 'SSL_CERT_FILE' in os.environ:
                    del os.environ['SSL_CERT_FILE']
    
    @patch('src.tools.twitter_sentiment.TwitterSentimentTool._scrape_tweets')
    @patch('datetime.datetime')
    def test_run_with_date_checks(self, mock_datetime, mock_scrape):
        """Test handling of potentially incorrect system dates."""
        # Mock current time to be in the future
        mock_now = MagicMock()
        mock_now.year = 2030  # Future year
        mock_datetime.now.return_value = mock_now
        
        # Mock scrape_tweets to return empty list
        mock_scrape.return_value = []
        
        # Run should still work with synthetic data
        result = self.tool.run("BTC", 10)
        
        # Verify result is valid
        self.assertEqual(result["symbol"], "BTC")
        self.assertIn("average_sentiment", result)
        self.assertIn("tweet_count", result)
        self.assertIn("sample_tweets", result)

    def test_scrape_tweets_python_with_ssl_error(self):
        """Test scraping tweets with SSL error."""
        # Test a simpler case - with mocked ssl context
        with patch('ssl._create_unverified_context') as mock_ssl_context:
            # Make SSL throw an error
            mock_ssl_context.side_effect = ssl.SSLError("Certificate verify failed")
            
            # Call the method with try/except to handle import errors
            try:
                result = self.tool._scrape_tweets_python("BTC", 10)
                # Verify the result is an empty list
                self.assertEqual(result, [])
            except ImportError:
                # Skip test if snscrape is not available
                self.skipTest("snscrape module not available")
    
    def test_scrape_tweets_python_future_date(self):
        """Test scraping tweets with future system date."""
        # Use a simpler approach to just test the date handling
        with patch('src.tools.twitter_sentiment.datetime') as mock_datetime:
            # Mock future date detection (year > 2023)
            future_date = MagicMock()
            future_date.year = 2025
            mock_datetime.datetime.now.return_value = future_date
            
            # Also mock the date subtraction for test stability
            fixed_date = MagicMock()
            fixed_date.year = 2023
            fixed_date.month = 1
            fixed_date.day = 1
            mock_datetime.datetime.return_value = fixed_date
            
            # Create a mock for ssl._create_default_https_context to avoid actual network calls
            with patch('ssl._create_default_https_context'):
                with patch('ssl._create_unverified_context'):
                    # Call the method with try/except to handle import errors
                    try:
                        self.tool._scrape_tweets_python("BTC", 10)
                        # If we get here without exception, test passes
                    except ImportError:
                        # Skip test if snscrape is not available
                        self.skipTest("snscrape module not available")
    
    def test_get_sentiment_label_all_ranges(self):
        """Test all possible sentiment label ranges."""
        # Test very positive sentiment
        self.assertEqual(self.tool._get_sentiment_label(0.8), "Very Positive")
        self.assertEqual(self.tool._get_sentiment_label(0.5), "Very Positive")
        
        # Test positive sentiment
        self.assertEqual(self.tool._get_sentiment_label(0.4), "Positive")
        self.assertEqual(self.tool._get_sentiment_label(0.1), "Positive")
        
        # Test very negative sentiment
        self.assertEqual(self.tool._get_sentiment_label(-0.8), "Very Negative")
        self.assertEqual(self.tool._get_sentiment_label(-0.5), "Very Negative")
        
        # Test negative sentiment
        self.assertEqual(self.tool._get_sentiment_label(-0.4), "Negative")
        self.assertEqual(self.tool._get_sentiment_label(-0.1), "Negative")
        
        # Test neutral sentiment
        self.assertEqual(self.tool._get_sentiment_label(0.09), "Neutral")
        self.assertEqual(self.tool._get_sentiment_label(-0.09), "Neutral")
        self.assertEqual(self.tool._get_sentiment_label(0), "Neutral")
    
    @patch('time.sleep', return_value=None)
    def test_scrape_tweets_subprocess_timeout(self, mock_sleep):
        """Test scraping tweets with subprocess timeout."""
        with patch('subprocess.Popen') as mock_popen:
            # Mock the subprocess.Popen to simulate a timeout
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            mock_process.communicate.side_effect = subprocess.TimeoutExpired(cmd=['snscrape'], timeout=30)
            
            # Call the method
            result = self.tool._scrape_tweets("ETH", 10)
            
            # Verify the result is an empty list (fallback to empty list on error)
            self.assertEqual(result, [])

    def test_scrape_tweets_with_invalid_json(self):
        """Test scraping tweets with invalid JSON output."""
        with patch('subprocess.Popen') as mock_popen:
            # Mock process that returns invalid JSON
            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            # Return some invalid JSON in stdout
            mock_process.communicate.return_value = ("invalid json data\n{broken:json:format}", "")
            
            # Call the method
            result = self.tool._scrape_tweets("LTC", 10)
            
            # Verify the result is an empty list since JSON parsing would fail
            self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main() 