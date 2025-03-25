"""Main entry point for the LLM trading agent."""

import argparse
import logging
import sys

from .llm_engine import LLMEngine
from .utils import setup_logger, get_user_input, display_results
from . import config

logger = setup_logger("main")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="LLM-powered trading agent for Hyperliquid")
    
    parser.add_argument("--prompt", type=str, default=None,
                        help="Trading instruction prompt")
    parser.add_argument("--symbol", type=str, default="BTC",
                        help="Cryptocurrency symbol to trade (default: BTC)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run in dry-run mode without executing trades")
    parser.add_argument("--interactive", action="store_true",
                        help="Run in interactive mode")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    parser.add_argument("--amount", type=float, default=0.01,
                        help="Dollar amount available for trading (default: 0.01)")
    
    return parser.parse_args()

def main():
    """Main entry point."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure logging
    if args.debug:
        for logger_name in logging.root.manager.loggerDict:
            if logger_name.startswith("src"):
                logging.getLogger(logger_name).setLevel(logging.DEBUG)
        logging.getLogger("openai").setLevel(logging.DEBUG)
    
    # Display configuration info
    config.display_config_info()
    
    # Get user input in interactive mode
    if args.interactive:
        user_input = get_user_input()
        prompt = user_input["prompt"]
        symbol = user_input["symbol"]
        dry_run = user_input["dry_run"]
        amount = user_input["amount"]
    else:
        # Use command line arguments
        if not args.prompt:
            print("Error: No prompt provided. Use --prompt or --interactive.")
            sys.exit(1)
        prompt = args.prompt
        symbol = args.symbol
        dry_run = args.dry_run
        amount = args.amount
    
    # Add a warning message about the amount parameter to ensure it's intentional
    if amount > 100:
        logger.warning(f"ATTENTION: Trading with a large amount (${amount}). Make sure this is intentional.")
        print(f"\nWARNING: Trading with a large amount (${amount}). Make sure this is intentional.")
    elif amount <= 0.1:
        logger.info(f"Trading with a small amount (${amount}). This is fine for testing.")
        print(f"\nNote: Trading with a small amount (${amount}).")
    
    logger.info(f"Starting trading agent with prompt: '{prompt}' for symbol: {symbol}, amount: ${amount}")
    
    try:
        # Initialize LLM engine
        llm_engine = LLMEngine()
        
        # Process the prompt - the LLM will decide which tools to use
        # including trading execution if appropriate
        result = llm_engine.process_prompt(prompt, symbol, dry_run=dry_run, amount=amount)
        
        if not result:
            logger.error("Failed to get results from LLM engine")
            print("Error: Failed to get results from LLM engine")
            return
        
        # Display results
        display_results(result)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 