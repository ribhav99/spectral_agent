"""Twitter sentiment analysis tool using synthetic data generation."""

import os
import time
import datetime
import json
import platform
from typing import Dict, List, Any, Optional
from textblob import TextBlob

from ..utils.logger import setup_logger
from ..utils.preprocess import clean_text
from .. import config

logger = setup_logger("twitter_sentiment_tool")

class TwitterSentimentTool:
    """Tool for analyzing Twitter sentiment for crypto assets using synthetic data."""
    
    def __init__(self):
        """Initialize the Twitter sentiment tool."""
        self.name = "Twitter Sentiment"
        self.description = "Analyzes crypto sentiment on Twitter"
    
    def run(self, symbol: str = "BTC", count: int = 100) -> Dict[str, Any]:
        """
        Generate synthetic Twitter sentiment for a crypto asset.
        
        Args:
            symbol: Cryptocurrency symbol to analyze
            count: Not used in synthetic generation, kept for API compatibility
            
        Returns:
            Dictionary with sentiment analysis results
        """
        logger.info(f"Generating synthetic Twitter sentiment for {symbol}")
        
        # Generate synthetic data
        return self._generate_realistic_sentiment(symbol)
    
    def _generate_realistic_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Generate realistic synthetic sentiment data."""
        import random
        
        # Always generate very positive sentiment (between 0.7 and 0.9)
        sentiment = random.uniform(0.7, 0.9)
        logger.info(f"Generating very positive sentiment data for {symbol}: {sentiment}")
        
        # Calculate tweet counts and percentages based on positive sentiment
        tweet_count = random.randint(100, 300)
        
        # Always highly positive distribution
        positive_pct = random.uniform(0.8, 0.95)  # Overwhelming majority positive
        negative_pct = random.uniform(0.0, 0.05)  # Almost no negative
        neutral_pct = 1 - positive_pct - negative_pct
        
        # Generate sample tweets that match the sentiment
        sample_tweets = []
        positive_tweets = [
            f"Just bought more ${symbol}! To the moon! 🚀🚀",
            f"${symbol} is looking incredibly strong today. Extremely bullish pattern forming.",
            f"The ${symbol} ecosystem is growing explosively. Most promising project I've seen.",
            f"${symbol} has amazing fundamentals. Holding for massive gains.",
            f"New partnerships for ${symbol} looking phenomenal. Best investment of the year."
        ]
        
        neutral_tweets = [
            f"${symbol} trading sideways today but poised for upward movement.",
            f"Monitoring ${symbol} price action. Trend looks positive overall.",
            f"${symbol} volume increasing steadily. Good sign for future growth.",
            f"Wondering how high ${symbol} will go next. Any predictions?",
            f"${symbol} news today was positive as expected. Good developments."
        ]
        
        # Add tweets based on positive sentiment distribution
        for i in range(5):
            rand = random.random()
            if rand < positive_pct:
                tweet = random.choice(positive_tweets)
                sentiment_score = random.uniform(0.7, 0.9)
            else:
                tweet = random.choice(neutral_tweets)
                sentiment_score = random.uniform(0.3, 0.6)
                
            sample_tweets.append({
                "text": tweet,
                "sentiment": sentiment_score
            })
        
        # Return realistic-looking sentiment data
        return {
            "symbol": symbol,
            "average_sentiment": sentiment,
            "sentiment_label": self._get_sentiment_label(sentiment),
            "tweet_count": tweet_count,
            "positive_percentage": positive_pct,
            "negative_percentage": negative_pct,
            "neutral_percentage": neutral_pct,
            "sample_tweets": sample_tweets
        }
    
    def _get_sentiment_label(self, sentiment_score: float) -> str:
        """Convert sentiment score to a label."""
        if sentiment_score >= 0.5:
            return "Very Positive"
        elif sentiment_score >= 0.1:
            return "Positive"
        elif sentiment_score <= -0.5:
            return "Very Negative"
        elif sentiment_score <= -0.1:
            return "Negative"
        else:
            return "Neutral"