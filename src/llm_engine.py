"""LLM Engine for interacting with OpenAI."""

import inspect
import json
import os
import time
from typing import Any, Dict, List, Optional, Type, Union, Callable
import logging

import openai
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from dotenv import load_dotenv

from .tools.twitter_sentiment import TwitterSentimentTool
from .tools.market_data import MarketDataTool
from .tools.trading_execution import TradingExecutionTool
from .utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Set up logger
logger = setup_logger("llm_engine")

# Custom JSON encoder for OpenAI objects
class OpenAIEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles OpenAI objects."""
    
    def default(self, obj):
        # Handle OpenAI objects
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        
        # Handle ChatCompletionMessageToolCall objects
        if isinstance(obj, ChatCompletionMessageToolCall):
            return {
                "id": obj.id,
                "type": obj.type,
                "function": {
                    "name": obj.function.name,
                    "arguments": obj.function.arguments
                }
            }
            
        # Handle any other object with __dict__
        if hasattr(obj, "__dict__"):
            return obj.__dict__
            
        return super().default(obj)

class LLMEngine:
    """
    LLM Engine for interacting with OpenAI and executing appropriate tools based on user input.
    """
    
    # Available tools
    AVAILABLE_TOOLS = {
        "TwitterSentimentTool": TwitterSentimentTool,
        "MarketDataTool": MarketDataTool
    }
    
    # Tools that are executed manually (not available to LLM)
    MANUAL_TOOLS = {
        "TradingExecutionTool": TradingExecutionTool
    }
    
    def __init__(self):
        """Initialize the LLM Engine."""
        self.tools = {}  # Will lazy load tools when needed
        self.tool_specs = None
        logger.info("LLM Engine initialized with lazy loading of tools")
        
    def _get_tool_instance(self, tool_name: str) -> Any:
        """Lazy load and return a tool instance."""
        if tool_name not in self.tools:
            if tool_name not in self.AVAILABLE_TOOLS:
                logger.warning(f"Unknown tool requested: {tool_name}")
                return None
                
            logger.info(f"Lazy loading tool: {tool_name}")
            tool_class = self.AVAILABLE_TOOLS[tool_name]
            self.tools[tool_name] = tool_class()
            
        return self.tools[tool_name]
    
    def _generate_tool_specs(self) -> List[Dict[str, Any]]:
        """Generate specifications for all available tools."""
        specs = []
        for tool_name, tool_class in self.AVAILABLE_TOOLS.items():
            # Create a temporary instance to extract specifications
            temp_instance = tool_class()
            methods = inspect.getmembers(temp_instance, predicate=inspect.ismethod)
            
            for method_name, method in methods:
                # Skip private methods and special methods
                if method_name.startswith('_') or method_name in ['__init__', '__call__']:
                    continue
                
                # Get function signature
                sig = inspect.signature(method)
                
                # Extract parameters information
                parameters = {}
                required_params = []
                
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    
                    # Get parameter type hint if available
                    param_type = "string"
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation == str:
                            param_type = "string"
                        elif param.annotation == int:
                            param_type = "integer"
                        elif param.annotation == float:
                            param_type = "number"
                        elif param.annotation == bool:
                            param_type = "boolean"
                        elif param.annotation == dict or param.annotation == Dict:
                            param_type = "object"
                        elif param.annotation == list or param.annotation == List:
                            param_type = "array"
                
                    # Parameter description
                    param_description = f"Parameter {param_name} for the {method_name} method"
                    
                    # Add parameter to spec
                    parameters[param_name] = {
                        "type": param_type,
                        "description": param_description
                    }
                    
                    # Check if parameter is required
                    if param.default == inspect.Parameter.empty:
                        required_params.append(param_name)
                
                # Get function docstring
                docstring = inspect.getdoc(method) or f"Execute the {method_name} method of {tool_name}"
                
                # Create function specification
                func_name = f"{tool_name}_{method_name}"  # Use underscore instead of dot
                func_spec = {
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "description": docstring,
                        "parameters": {
                            "type": "object",
                            "properties": parameters,
                            "required": required_params
                        }
                    }
                }
                
                specs.append(func_spec)
                
        logger.debug(f"Generated {len(specs)} tool specifications")
        return specs
    
    def process_prompt(self, prompt: str, symbol: str, dry_run: bool = True, amount: float = 100.0) -> Dict[str, Any]:
        """
        Process a user prompt and execute appropriate tools.
        
        Args:
            prompt: The user prompt to process
            symbol: The cryptocurrency symbol to analyze
            dry_run: Whether to run in dry-run mode
            amount: Dollar amount available for trading
            
        Returns:
            Dict containing the results
        """
        logger.info(f"Processing prompt: '{prompt}' for symbol {symbol}, dry_run={dry_run}, amount=${amount}")
        
        # Create the initial context
        context = {
            "prompt": prompt,
            "symbol": symbol,
            "dry_run": dry_run,
            "amount": amount,
            "start_time": time.time(),
            "tool_results": {}
        }
        
        try:
            # Generate tool specifications if not already done
            if self.tool_specs is None:
                self.tool_specs = self._generate_tool_specs()
            
            # Validate tool specs
            if not self.tool_specs or len(self.tool_specs) == 0:
                logger.error("No tool specifications were generated")
                return {
                    "symbol": symbol,
                    "message": "Failed to initialize tools",
                    "error": "No tool specifications were generated",
                    "timestamp": int(time.time())
                }
            
            # Log all available tools for debugging
            tool_names = [spec["function"]["name"] for spec in self.tool_specs]
            logger.info(f"Available tools: {', '.join(tool_names)}")
            
            # Create chat state to track message history
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": f"I want to {prompt} for {symbol}"}
            ]
            
            # Track if any tool calls were made
            made_tool_calls = False
            
            # Maximum number of turns in the conversation
            max_turns = 5
            turn_count = 0
            
            # Initialize assistant_message to None
            assistant_message = None
            
            while turn_count < max_turns:
                turn_count += 1
                logger.info(f"Starting conversation turn {turn_count}/{max_turns}")
                
                # Log the current messages being sent to OpenAI
                try:
                    # Use custom encoder for OpenAI objects
                    logger.debug(f"Sending messages to OpenAI: {json.dumps(messages, indent=2, cls=OpenAIEncoder)}")
                except Exception as e:
                    logger.warning(f"Failed to serialize messages for logging: {str(e)}")
                
                try:
                    response = openai.chat.completions.create(
                        model="gpt-4o",
                        # model="o3-mini-high",
                        messages=messages,
                        tools=self.tool_specs,
                        temperature=0.1
                    )
                    
                    # Log the response from OpenAI
                    try:
                        logger.debug(f"Received response from OpenAI: {json.dumps(response.model_dump(), indent=2)}")
                    except Exception as e:
                        logger.warning(f"Failed to serialize OpenAI response for logging: {str(e)}")
                    
                    assistant_message = response.choices[0].message
                    
                    # Add assistant message to history (convert to dict for JSON serialization)
                    messages.append({
                        "role": "assistant", 
                        "content": assistant_message.content or "",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            } for tool_call in (assistant_message.tool_calls or [])
                        ]
                    })
                    
                    # Check if there are tool calls
                    if assistant_message.tool_calls:
                        made_tool_calls = True
                        logger.info(f"LLM requested {len(assistant_message.tool_calls)} tool calls")
                        
                        for tool_call in assistant_message.tool_calls:
                            tool_result = self._execute_tool_call(tool_call, context)
                            
                            # Add the tool result to the message history
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": self._serialize_tool_result(tool_result)
                            })
                    else:
                        logger.info("LLM did not request any tool calls in this turn")
                        
                        # Only break if this is the very first turn and the LLM isn't using tools
                        if turn_count == 1 and assistant_message.content:
                            logger.warning("LLM provided a response without making any tool calls")
                            break
                        
                        # If we've made tool calls already and now the LLM provides content without tool calls,
                        # we'll break out of the loop and check for task completion outside
                        if made_tool_calls and assistant_message.content:
                            logger.info("LLM stopped making tool calls, will check if task is complete")
                            break
                            
                        # If the LLM provided no content and no tool calls, there's an issue
                        if not assistant_message.content:
                            logger.warning("LLM provided no content and no tool calls - this should not happen")
                            break
                
                except Exception as e:
                    logger.error(f"Error during OpenAI API call: {str(e)}", exc_info=True)
                    context["error"] = str(e)
                    break
            
            # Check if the LLM made any tool calls
            if not made_tool_calls:
                logger.warning("LLM did not request any tool calls, ending conversation")
                if assistant_message and assistant_message.content:
                    context["message"] = assistant_message.content
                return context
                
            # If we have tool calls but the LLM didn't request any more in the last turn,
            # execute the trading tool
            if assistant_message and not assistant_message.tool_calls and made_tool_calls:
                # Check if TradingExecutionTool was already called (should never happen now)
                trading_tool_used = False
                if "tool_results" in context and isinstance(context["tool_results"], dict):
                    for tool_key in context["tool_results"].keys():
                        if tool_key.startswith("TradingExecutionTool"):
                            trading_tool_used = True
                            logger.info("TradingExecutionTool was already called, task is complete")
                            break
                
                # Execute trading tool if it wasn't used yet
                if not trading_tool_used:
                    logger.info("LLM stopped calling tools - executing TradingExecutionTool automatically")
                    
                    # Ask the LLM for a final recommendation
                    final_recommendation_messages = [
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": f"I want to {prompt} for {symbol}. Based on your analysis, what's your final trading recommendation? Should I go LONG, SHORT, or NEUTRAL on {symbol}? Please provide a clear recommendation with reasoning."}
                    ]
                    
                    # Add a summary of the context
                    context_summary = ""
                    if "tool_results" in context and isinstance(context["tool_results"], dict):
                        context_summary = "Here's the data we've gathered:\n"
                        
                        # Include any market data
                        market_data = None
                        for tool_key, tool_result in context["tool_results"].items():
                            if tool_key.startswith("MarketDataTool") and isinstance(tool_result, dict):
                                market_data = tool_result
                                context_summary += f"- Market price for {tool_result.get('symbol')}: ${tool_result.get('current_price')}\n"
                                if 'market_trend' in tool_result:
                                    context_summary += f"- Market trend: {tool_result.get('market_trend')}\n"
                                break
                                
                        # Include any sentiment data
                        sentiment_data = None
                        for tool_key, tool_result in context["tool_results"].items():
                            if tool_key.startswith("TwitterSentimentTool") and isinstance(tool_result, dict):
                                sentiment_data = tool_result
                                context_summary += f"- Twitter sentiment: {tool_result.get('sentiment_label')} ({tool_result.get('average_sentiment')})\n"
                                context_summary += f"- Tweet count: {tool_result.get('tweet_count')}\n"
                                break
                    
                    if context_summary:
                        final_recommendation_messages.append({"role": "user", "content": context_summary})
                    
                    try:
                        logger.debug(f"Requesting final recommendation")
                        recommendation_response = openai.chat.completions.create(
                            model="gpt-4o",
                            messages=final_recommendation_messages,
                            temperature=0.1
                        )
                        
                        recommendation_message = recommendation_response.choices[0].message
                        recommendation_content = recommendation_message.content or ""
                        
                        # Parse the recommendation to determine direction
                        direction = None
                        if "LONG" in recommendation_content.upper():
                            direction = "LONG"
                        elif "SHORT" in recommendation_content.upper():
                            direction = "SHORT"
                        else:
                            direction = "NEUTRAL"
                        
                        logger.info(f"Final recommendation: {direction}")
                        
                        # Always execute the trade tool, even for NEUTRAL recommendations
                        # The trading tool will handle the recommendation and any order size validations
                        try:
                            from .tools.trading_execution import TradingExecutionTool
                            trade_tool = TradingExecutionTool()
                            
                            # For NEUTRAL recommendations, we'll still call the tool but with a specific direction
                            # The tool can make its own determination or respect the NEUTRAL recommendation
                            
                            # Prepare arguments for trading
                            trading_args = {
                                "symbol": symbol,
                                "direction": direction,
                                "amount": amount,
                                "dry_run": dry_run
                            }
                            
                            # Add market data if available
                            if "tool_results" in context and isinstance(context["tool_results"], dict):
                                for tool_key, tool_result in context["tool_results"].items():
                                    if tool_key.startswith("MarketDataTool") and isinstance(tool_result, dict) and "current_price" in tool_result:
                                        trading_args["market_data"] = tool_result
                                        logger.info(f"Adding market data to trading args: {tool_result.get('symbol')} at ${tool_result.get('current_price')}")
                                        break
                            
                            # Add sentiment data if available
                            if "tool_results" in context and isinstance(context["tool_results"], dict):
                                for tool_key, tool_result in context["tool_results"].items():
                                    if tool_key.startswith("TwitterSentimentTool") and isinstance(tool_result, dict) and "average_sentiment" in tool_result:
                                        trading_args["sentiment_data"] = tool_result
                                        logger.info(f"Adding sentiment data to trading args: {tool_result.get('sentiment_label')} ({tool_result.get('average_sentiment')})")
                                        break
                                        
                            trade_result = trade_tool.run(**trading_args)
                            context["tool_results"]["TradingExecutionTool_run"] = trade_result
                            
                            if direction == "NEUTRAL":
                                logger.info(f"NEUTRAL recommendation - Trading tool executed with result: {trade_result}")
                            else:
                                logger.info(f"Trade executed with result: {trade_result}")
                                
                        except Exception as e:
                            logger.error(f"Error executing trade: {str(e)}", exc_info=True)
                            context["trade_error"] = str(e)
                    
                    except Exception as e:
                        logger.error(f"Error during trading execution: {str(e)}", exc_info=True)
            
            # Add the final message if there is one and wasn't set during trading execution
            if assistant_message and assistant_message.content and "message" not in context:
                context["message"] = assistant_message.content
            
            # Calculate elapsed time
            elapsed_time = time.time() - context.get("start_time", time.time())
            context["elapsed_time"] = round(elapsed_time, 2)
            logger.info(f"Prompt processing completed in {elapsed_time:.2f} seconds")
            
            return context
            
        except Exception as e:
            logger.error(f"Unexpected error in process_prompt: {str(e)}", exc_info=True)
            return {
                "symbol": symbol,
                "error": str(e),
                "message": "An error occurred while processing your request",
                "timestamp": int(time.time())
            }
    
    def _execute_tool_call(self, tool_call: ChatCompletionMessageToolCall, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a requested tool call and return the result.
        
        Args:
            tool_call: The tool call request from OpenAI
            context: The current context dictionary
            
        Returns:
            The result of the tool execution
        """
        try:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            logger.info(f"Executing tool call: {function_name} with args: {function_args}")
            
            # Parse the function name to get tool name and method
            if "_" in function_name:
                tool_name, method_name = function_name.split("_", 1)
            else:
                logger.error(f"Invalid function name format: {function_name}")
                return {"error": f"Invalid function name format: {function_name}"}
            
            # Get the tool instance
            tool_instance = self._get_tool_instance(tool_name)
            if not tool_instance:
                logger.error(f"Tool not found: {tool_name}")
                return {"error": f"Tool not found: {tool_name}"}
            
            # Get the method
            method = getattr(tool_instance, method_name, None)
            if not method:
                logger.error(f"Method not found: {tool_name}.{method_name}")
                return {"error": f"Method not found: {tool_name}.{method_name}"}
            
            # Add relevant context to function args
            if "symbol" in inspect.signature(method).parameters and "symbol" not in function_args:
                function_args["symbol"] = context.get("symbol")
            
            if "dry_run" in inspect.signature(method).parameters and "dry_run" not in function_args:
                function_args["dry_run"] = context.get("dry_run", True)
            
            if "amount" in inspect.signature(method).parameters and "amount" not in function_args:
                function_args["amount"] = context.get("amount", 100.0)
            
            # If this is a trading tool, pass any market data we've already fetched
            if tool_name == "TradingExecutionTool":
                # Pass market data if parameter exists
                if "market_data" in inspect.signature(method).parameters:
                    # Look for market data in the context
                    market_data = None
                    
                    # Check for direct market data results
                    if "current_price" in context and "symbol" in context:
                        # Create market data dictionary from context
                        market_data = {
                            "symbol": context.get("symbol"),
                            "current_price": context.get("current_price")
                        }
                        logger.info(f"Passing market data from context to trading tool: {context.get('symbol')} at ${context.get('current_price')}")
                    
                    # Check for tool results from MarketDataTool
                    elif "tool_results" in context and isinstance(context["tool_results"], dict):
                        for tool_key, tool_result in context["tool_results"].items():
                            if tool_key.startswith("MarketDataTool") and isinstance(tool_result, dict) and "current_price" in tool_result:
                                market_data = tool_result
                                logger.info(f"Passing market data from previous tool result to trading tool: {tool_result.get('symbol')} at ${tool_result.get('current_price')}")
                                break
                    
                    # If market data was found, add it to function args
                    if market_data:
                        function_args["market_data"] = market_data
                
                # Pass sentiment data if parameter exists
                if "sentiment_data" in inspect.signature(method).parameters:
                    # Look for sentiment data in the context
                    sentiment_data = None
                    
                    # Check for direct sentiment results
                    if "average_sentiment" in context:
                        # Create sentiment data dictionary from context
                        sentiment_data = {
                            "average_sentiment": context.get("average_sentiment"),
                            "sentiment_label": context.get("sentiment_label", ""),
                            "tweet_count": context.get("tweet_count", 0)
                        }
                        logger.info(f"Passing sentiment data from context to trading tool: {sentiment_data}")
                    
                    # Check for tool results from TwitterSentimentTool
                    elif "tool_results" in context and isinstance(context["tool_results"], dict):
                        for tool_key, tool_result in context["tool_results"].items():
                            if tool_key.startswith("TwitterSentimentTool") and isinstance(tool_result, dict) and "average_sentiment" in tool_result:
                                sentiment_data = tool_result
                                logger.info(f"Passing sentiment data from previous tool result to trading tool: {tool_result.get('sentiment_label')} ({tool_result.get('average_sentiment')})")
                                break
                    
                    # If sentiment data was found, add it to function args
                    if sentiment_data:
                        function_args["sentiment_data"] = sentiment_data
            
            # Execute the method
            start_time = time.time()
            result = method(**function_args)
            elapsed = time.time() - start_time
            
            # Print the tool result immediately
            print("\n===== Tool Execution Result =====")
            print(f"Tool: {function_name}")
            
            # Format and print the result based on its type
            if isinstance(result, dict):
                for key, value in result.items():
                    # Skip large nested structures but indicate they exist
                    if isinstance(value, (dict, list)) and len(str(value)) > 100:
                        print(f"  {key}: [Complex data structure]")
                    else:
                        print(f"  {key}: {value}")
            elif isinstance(result, list) and len(result) > 0:
                # For lists, print a summary
                print(f"  [List with {len(result)} items]")
                # Print first item as example if it's a simple type
                if len(result) > 0 and not isinstance(result[0], (dict, list)):
                    print(f"  Example: {result[0]}")
            else:
                # For simple types, print directly
                print(f"  {result}")
            
            logger.info(f"Tool {function_name} executed in {elapsed:.2f}s")
            logger.debug(f"Tool result: {result}")
            
            # Store the result in the context
            tool_key = f"{tool_name}_{method_name}"  # Use underscore to match function naming
            if "tool_results" not in context:
                context["tool_results"] = {}
            context["tool_results"][tool_key] = result
            
            # Update context with results
            if isinstance(result, dict):
                # Don't overwrite existing keys
                for key, value in result.items():
                    if key not in context:
                        context[key] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool call: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for the LLM.
        
        Returns:
            The system prompt as a string
        """
        return """You are an advanced trading agent that helps users execute cryptocurrency trades.
You have access to a range of tools:

1. TwitterSentimentTool - Analyze social media sentiment for cryptocurrencies
2. MarketDataTool - Get current market data, prices, and technical indicators
3. TradingExecutionTool - Execute trades on exchanges

When users ask you a question or request:
1. CAREFULLY think about which tools will help answer their query
2. Call the tools in a logical sequence to gather necessary information
3. Only call tools that are needed - don't use tools that aren't relevant
4. If you need market data or sentiment analysis for a trading decision, use those tools before making a decision
5. When executing trades, ALWAYS use the dry_run parameter provided in the context, never override it
6. When executing trades, ALWAYS use the EXACT amount parameter provided in the context
7. NEVER modify, override, or substitute the amount value with your own value
8. The amount parameter represents the TOTAL dollar amount available for trading, not a position size

IMPORTANT: You MUST use tools to complete the trading task. Do not respond with only text.
For any trading request, you must at minimum use the MarketDataTool to get current prices and the TradingExecutionTool to execute the trade.

For example, if a user asks to "trade based on sentiment" with an amount of $0.5:
1. Call TwitterSentimentTool to analyze sentiment
2. Call MarketDataTool to get current price information
3. Call TradingExecutionTool to execute the trade based on the sentiment and market data using EXACTLY $0.5 as the amount parameter

CRITICALLY IMPORTANT:
- Every trading task MUST end with a TradingExecutionTool call
- Never skip calling tools - they are essential to completing the task
- You will be asked to confirm if you've completed the task - only answer yes if you've called all necessary tools
- Do not ask the user for any further inputs - use the provided context
- If additional tools or information are needed, call the appropriate tools

Respect the parameters provided in the context. These are user preferences and should never be changed.
Provide clear, concise responses about what you've done and your results.
"""

    def _serialize_tool_result(self, result: Any) -> str:
        """
        Safely serialize tool result to JSON string.
        
        Args:
            result: The result to serialize
            
        Returns:
            JSON string representation of the result
        """
        try:
            return json.dumps(result, cls=OpenAIEncoder, default=str)
        except Exception as e:
            logger.error(f"Error serializing tool result: {str(e)}")
            # Fall back to simple string representation
            return str(result)

    def _get_manual_tool_instance(self, tool_name: str) -> Any:
        """
        Get a manual tool instance.
        
        Args:
            tool_name: The name of the tool to get
            
        Returns:
            The tool instance
        """
        if tool_name in self.MANUAL_TOOLS:
            logger.info(f"Getting manual tool instance: {tool_name}")
            return self.MANUAL_TOOLS[tool_name]()
        else:
            logger.warning(f"Unknown manual tool requested: {tool_name}")
            return None 