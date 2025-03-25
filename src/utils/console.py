"""Utility functions for console I/O and result display."""

import json
import time
from typing import Dict, Any

from .logger import setup_logger

logger = setup_logger("console_utils")

def get_user_input() -> Dict[str, Any]:
    """Get user input in interactive mode."""
    print("\n===== LLM Trading Agent =====")
    print("Enter your trading instruction (e.g., 'trade using sentiment'):")
    prompt = input("> ")
    
    print("\nEnter cryptocurrency symbol (default: BTC):")
    symbol = input("> ")
    if not symbol:
        symbol = "BTC"
    
    print("\nEnter dollar amount available for trading (default: 100.0):")
    amount_input = input("> ")
    amount = 100.0
    if amount_input:
        try:
            amount = float(amount_input)
        except ValueError:
            print("Invalid amount, using default: 100.0")
    
    print("\nDry run? (y/n, default: y):")
    dry_run_input = input("> ")
    dry_run = dry_run_input.lower() != "n"
    
    return {
        "prompt": prompt,
        "symbol": symbol,
        "dry_run": dry_run,
        "amount": amount
    }

def display_results(results: Dict[str, Any]) -> None:
    """Display trading results in a user-friendly format."""
    if not results:
        print("No results to display")
        return
        
    print("\n===== Results =====")
    
    # Check if there's an error status
    if results.get("status") == "error":
        print(f"\nError: {results.get('message', 'Unknown error')}")
        print(f"  Symbol: {results.get('symbol', 'Unknown')}")
        print(f"  Timestamp: {results.get('timestamp', 0)}")
        return
    
    # Check if there's a main message
    if "message" in results:
        print(f"\nMessage: {results['message']}")
    
    # Check if it's a decision result
    if "decision" in results:
        print(f"\nTrading Decision:")
        print(f"  Symbol: {results.get('symbol', 'Unknown')}")
        print(f"  Decision: {results.get('decision', 'Unknown')}")
        print(f"  Confidence: {results.get('confidence', 0) * 100:.1f}%")
        print(f"  Reasoning: {results.get('reasoning', '')}")
        
        # Show position information for trades that will be executed
        if results.get('decision') not in ["NEUTRAL", "NONE"]:
            print(f"  Position Size: {results.get('position_size', 0) * 100:.1f}%")
            print(f"  Stop Loss: {results.get('stop_loss', 0) * 100:.1f}%")
            print(f"  Take Profit: {results.get('take_profit', 0) * 100:.1f}%")
        else:
            print(f"  Action: {results.get('action', 'No trade executed')}")
            
        # Show market data used for decision if available    
        if 'market_data' in results and isinstance(results['market_data'], dict):
            market_data = results['market_data']
            print(f"\n  Market Data Used:")
            print(f"    Current Price: ${market_data.get('current_price', 0):.2f}")
            print(f"    24h Change: {market_data.get('24h_change_percent', 0):.2f}%")
            
            # Show indicators if available
            indicators = market_data.get('indicators', {})
            if indicators:
                print(f"    RSI: {indicators.get('rsi_14', indicators.get('rsi', 0)):.2f}")
                
        # Show sentiment data used for decision if available
        if 'sentiment_data' in results and isinstance(results['sentiment_data'], dict):
            sentiment_data = results['sentiment_data']
            print(f"\n  Sentiment Data Used:")
            print(f"    Average Sentiment: {sentiment_data.get('average_sentiment', 0):.2f}")
            print(f"    Sentiment Label: {sentiment_data.get('sentiment_label', 'unknown')}")
            print(f"    Tweet Count: {sentiment_data.get('tweet_count', 0)}")
            
        # If amount was specified, show it
        if 'trading_amount' in results:
            print(f"\n  Trading Amount: ${results.get('trading_amount', 0):.2f}")
        
    # Check if it's a trade execution result
    elif "execution_result" in results:
        print(f"\nTrade Execution:")
        print(f"  Symbol: {results.get('symbol', 'Unknown')}")
        print(f"  Direction: {results.get('direction', 'Unknown')}")
        print(f"  Entry Price: ${results.get('entry_price', 0):.2f}")
        print(f"  Position Size: ${results.get('position_size_usd', 0):.2f}")
        print(f"  Stop Loss Price: ${results.get('stop_loss_price', 0):.2f}")
        print(f"  Take Profit Price: ${results.get('take_profit_price', 0):.2f}")
        
        # Show execution status
        execution = results.get('execution_result', {})
        status = execution.get('status', 'unknown')
        print(f"  Execution Status: {status}")
        
        if status == "error":
            print(f"  Error: {execution.get('message', 'Unknown error')}")
        elif execution.get('is_dry_run'):
            print("  This was a dry run (no actual trade executed)")
        elif execution.get('is_simulation'):
            print("  This was a simulation (no actual trade executed)")
    
    # Display market data if available
    if "current_price" in results:
        print(f"\nMarket Data:")
        # Safely handle None values with a default
        current_price = results.get('current_price')
        if current_price is not None:
            print(f"  Current Price: ${current_price:.2f}")
        else:
            print(f"  Current Price: Not available")
            
        # Handle change percent safely
        change_percent = results.get('24h_change_percent')
        if change_percent is not None:
            print(f"  24h Change: {change_percent:.2f}%")
        else:
            print(f"  24h Change: Not available")
        
        # Show indicators if available
        indicators = results.get('indicators', {})
        if indicators:
            # Handle potentially None RSI value
            rsi = indicators.get('rsi_14') or indicators.get('rsi')
            if rsi is not None:
                print(f"  RSI: {rsi:.2f}")
            else:
                print(f"  RSI: Not available")
                
            # Check for MACD
            macd = indicators.get('macd')
            if macd is not None:
                print(f"  MACD: {macd:.4f}")
                
            # Check for Bollinger Bands
            bb_middle = indicators.get('bb_middle')
            if bb_middle is not None:
                print(f"  Bollinger Middle: ${bb_middle:.2f}")
                
            # Check for trend info (may not be available in new implementation)
            if 'trend' in indicators:
                print(f"  Trend: {indicators.get('trend', 'unknown')}")
                
            # Check for volatility info (may not be available in new implementation)
            if 'volatility' in indicators:
                print(f"  Volatility: {indicators.get('volatility', 'unknown')}")
            
        # Show synthetic data note
        if results.get('is_synthetic') or results.get('is_synthetic_data'):
            print(f"  Note: Using synthetic market data")
    
    # Display sentiment data if available
    if "average_sentiment" in results:
        print(f"\nSentiment Analysis:")
        print(f"  Average Sentiment: {results.get('average_sentiment', 0):.2f}")
        print(f"  Sentiment Label: {results.get('sentiment_label', 'unknown')}")
        print(f"  Positive %: {results.get('positive_percentage', 0) * 100:.1f}%")
        print(f"  Negative %: {results.get('negative_percentage', 0) * 100:.1f}%")
        print(f"  Tweet Count: {results.get('tweet_count', 0)}")
    
    # See if there are other tool results to display
    tool_results = results.get('tool_results', {})
    if tool_results and len(tool_results) > 0:
        print(f"\nTools Used: {', '.join(tool_results.keys())}")
        
        # Display the tool results for each tool
        print("\nTool Results:")
        for tool_name, tool_result in tool_results.items():
            print(f"  {tool_name}:")
            
            # Format the tool result based on its type
            if isinstance(tool_result, dict):
                # Print each key-value pair for dictionary results
                for key, value in tool_result.items():
                    # Skip large nested structures but indicate they exist
                    if isinstance(value, (dict, list)) and len(str(value)) > 100:
                        print(f"    {key}: [Complex data structure]")
                    else:
                        print(f"    {key}: {value}")
            elif isinstance(tool_result, list) and len(tool_result) > 0:
                # For lists, print a summary
                print(f"    [List with {len(tool_result)} items]")
                # Print first item as example if it's a simple type
                if len(tool_result) > 0 and not isinstance(tool_result[0], (dict, list)):
                    print(f"    Example: {tool_result[0]}")
            else:
                # For simple types, print directly
                print(f"    {tool_result}")
    
    # Write results to file for reference
    try:
        import os
        
        # Create results directory if it doesn't exist
        results_dir = "results"
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = int(time.time())
        result_filename = f"result_{timestamp}.json"
        result_path = os.path.join(results_dir, result_filename)
        
        with open(result_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed results saved to {result_path}")
    except Exception as e:
        logger.error(f"Failed to write results file: {str(e)}") 