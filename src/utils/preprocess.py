import pandas as pd
import numpy as np
from datetime import datetime
import re
from typing import Dict, List, Union, Any

def clean_text(text: str) -> str:
    """
    Clean text data by removing special characters and normalizing.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
        
    # Remove URLs
    text = re.sub(r'http\S+', '', text)
    # Remove special characters and numbers
    text = re.sub(r'[^\w\s]', '', text)
    # Convert to lowercase
    text = text.lower().strip()
    
    return text

def normalize_market_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize market data to standardized format.
    
    Args:
        data: Raw market data
        
    Returns:
        Normalized market data
    """
    normalized = {}
    
    # Extract key metrics
    if 'price' in data:
        normalized['current_price'] = float(data['price'])
    
    if 'ohlc' in data:
        ohlc = data['ohlc']
        normalized['open'] = float(ohlc[0]) if len(ohlc) > 0 else None
        normalized['high'] = float(ohlc[1]) if len(ohlc) > 1 else None
        normalized['low'] = float(ohlc[2]) if len(ohlc) > 2 else None
        normalized['close'] = float(ohlc[3]) if len(ohlc) > 3 else None
    
    # Calculate volatility if high and low exist
    if 'high' in normalized and 'low' in normalized and normalized['high'] and normalized['low']:
        normalized['volatility'] = (normalized['high'] - normalized['low']) / normalized['low']
    
    return normalized

def format_for_llm_input(data: Dict[str, Any]) -> str:
    """
    Format data as string for LLM input.
    
    Args:
        data: Data to format
        
    Returns:
        Formatted string for LLM
    """
    output = []
    
    for key, value in data.items():
        # Format different value types
        if isinstance(value, float):
            formatted_value = f"{value:.6f}".rstrip('0').rstrip('.')
        elif isinstance(value, dict):
            formatted_value = format_for_llm_input(value)
        elif isinstance(value, list):
            formatted_value = ", ".join(str(item) for item in value)
        else:
            formatted_value = str(value)
            
        output.append(f"{key.replace('_', ' ').title()}: {formatted_value}")
    
    return "\n".join(output) 