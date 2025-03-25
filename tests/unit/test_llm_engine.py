import unittest
from unittest.mock import patch, MagicMock, ANY
import json
import time
import os

from src.llm_engine import LLMEngine, OpenAIEncoder

# Fix imports to match OpenAI library version 1.68.2
class MockChatCompletionMessageToolCall:
    def __init__(self, id, type, function):
        self.id = id
        self.type = type
        self.function = function

class MockChatCompletionMessageToolCallFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class TestOpenAIEncoder(unittest.TestCase):
    """Test the OpenAI JSON encoder."""
    
    def test_encoder_with_model_dump(self):
        """Test encoding objects with model_dump method."""
        obj = MagicMock()
        obj.model_dump.return_value = {"key": "value"}
        
        encoder = OpenAIEncoder()
        result = encoder.default(obj)
        
        self.assertEqual(result, {"key": "value"})
        obj.model_dump.assert_called_once()
    
    def test_encoder_with_tool_call(self):
        """Test encoding ChatCompletionMessageToolCall objects."""
        function = MagicMock()
        function.name = "test_function"
        function.arguments = '{"arg": "value"}'
        
        tool_call = MagicMock()
        tool_call.id = "call_123"
        tool_call.type = "function"
        tool_call.function = function
        
        encoder = OpenAIEncoder()
        result = encoder.default(tool_call)
        
        self.assertEqual(result, {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "test_function",
                "arguments": '{"arg": "value"}'
            }
        })
    
    def test_encoder_with_dict_obj(self):
        """Test encoding objects with __dict__."""
        class TestClass:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = "value2"
        
        obj = TestClass()
        encoder = OpenAIEncoder()
        result = encoder.default(obj)
        
        self.assertEqual(result, {"attr1": "value1", "attr2": "value2"})
    
    def test_encoder_fallback(self):
        """Test encoder fallback for unsupported types."""
        encoder = OpenAIEncoder()
        
        # This should raise TypeError as it falls back to super().default
        with self.assertRaises(TypeError):
            encoder.default(complex(1, 2))


class TestLLMEngine(unittest.TestCase):
    """Test the LLM Engine."""
    
    def setUp(self):
        """Set up for tests."""
        # Patch environment variables
        self.env_patcher = patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
        self.env_patcher.start()
        
        # Create the LLM engine
        self.engine = LLMEngine()
    
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    def test_init(self):
        """Test LLMEngine initialization."""
        self.assertEqual(self.engine.tools, {})
        self.assertIsNone(self.engine.tool_specs)
    
    @patch('src.llm_engine.TwitterSentimentTool')
    def test_get_tool_instance(self, mock_twitter_tool):
        """Test lazy loading of tool instances."""
        # Set up mock
        mock_instance = MagicMock()
        mock_twitter_tool.return_value = mock_instance
        
        # First call should create the instance
        result1 = self.engine._get_tool_instance("TwitterSentimentTool")
        self.assertEqual(result1, mock_instance)
        mock_twitter_tool.assert_called_once()
        
        # Second call should reuse the cached instance
        result2 = self.engine._get_tool_instance("TwitterSentimentTool")
        self.assertEqual(result2, mock_instance)
        mock_twitter_tool.assert_called_once()  # Still only called once
    
    def test_get_tool_instance_unknown(self):
        """Test getting an unknown tool."""
        result = self.engine._get_tool_instance("UnknownTool")
        self.assertIsNone(result)
    
    @patch('src.llm_engine.TwitterSentimentTool')
    @patch('src.llm_engine.MarketDataTool')
    def test_generate_tool_specs(self, mock_market_tool, mock_twitter_tool):
        """Test generation of tool specifications."""
        # Set up mocked tools with methods
        twitter_instance = MagicMock()
        twitter_instance.analyze_sentiment.return_value = {}
        twitter_instance.analyze_sentiment.__name__ = "analyze_sentiment"
        twitter_instance.analyze_sentiment.__doc__ = "Analyze sentiment for a cryptocurrency"
        sig = unittest.mock.create_autospec(twitter_instance.analyze_sentiment)
        sig.__signature__ = unittest.mock.create_autospec(sig.__signature__)
        twitter_instance.analyze_sentiment.__signature__ = sig.__signature__
        
        market_instance = MagicMock()
        market_instance.get_price.return_value = {}
        market_instance.get_price.__name__ = "get_price"
        market_instance.get_price.__doc__ = "Get current price for a cryptocurrency"
        sig2 = unittest.mock.create_autospec(market_instance.get_price)
        sig2.__signature__ = unittest.mock.create_autospec(sig2.__signature__)
        market_instance.get_price.__signature__ = sig2.__signature__
        
        mock_twitter_tool.return_value = twitter_instance
        mock_market_tool.return_value = market_instance
        
        # Generate tool specs
        specs = self.engine._generate_tool_specs()
        
        # We should have at least two tool specs (one for each tool method)
        self.assertGreaterEqual(len(specs), 2)
        
        # Check the specs format
        for spec in specs:
            self.assertEqual(spec["type"], "function")
            self.assertIn("function", spec)
            self.assertIn("name", spec["function"])
            self.assertIn("description", spec["function"])
            self.assertIn("parameters", spec["function"])
            self.assertIn("type", spec["function"]["parameters"])
            self.assertIn("properties", spec["function"]["parameters"])
            
            # Ensure the function name follows the expected format
            name = spec["function"]["name"]
            self.assertTrue("TwitterSentimentTool_" in name or "MarketDataTool_" in name)
    
    @patch('src.llm_engine.LLMEngine._generate_tool_specs')
    @patch('src.llm_engine.LLMEngine._get_system_prompt')
    @patch('src.llm_engine.openai.chat.completions.create')
    def test_process_prompt_no_tool_calls(self, mock_create, mock_get_system, mock_generate_specs):
        """Test processing a prompt without tool calls."""
        # Set up mocks
        mock_get_system.return_value = "System prompt"
        mock_generate_specs.return_value = [{"type": "function", "function": {"name": "test"}}]
        
        # Create a mock response
        mock_message = MagicMock()
        mock_message.content = "This is a response without tool calls"
        mock_message.tool_calls = None
        
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        
        mock_create.return_value = mock_response
        
        # Process a prompt
        result = self.engine.process_prompt("test prompt", "BTC")
        
        # Verify results
        self.assertIn("message", result)
        self.assertEqual(result["message"], "This is a response without tool calls")
        self.assertEqual(result["symbol"], "BTC")
        self.assertIn("tool_results", result)
        self.assertIn("elapsed_time", result)
        
        # Verify openai.chat.completions.create was called properly
        mock_create.assert_called_once()
        call_args = mock_create.call_args[1]
        self.assertEqual(call_args["model"], "gpt-4o")
        self.assertEqual(len(call_args["messages"]), 2)
        self.assertEqual(call_args["messages"][0]["role"], "system")
        self.assertEqual(call_args["messages"][1]["role"], "user")
        self.assertEqual(call_args["messages"][1]["content"], "I want to test prompt for BTC")
        self.assertEqual(call_args["tools"], mock_generate_specs.return_value)
    
    @patch('src.llm_engine.LLMEngine._execute_tool_call')
    @patch('src.llm_engine.LLMEngine._get_system_prompt')
    @patch('src.llm_engine.LLMEngine._generate_tool_specs')
    @patch('src.llm_engine.openai.chat.completions.create')
    def test_process_prompt_with_tool_calls(self, mock_create, mock_generate_specs, mock_get_system, mock_execute_tool):
        """Test processing a prompt with tool calls."""
        # Set up mocks
        mock_get_system.return_value = "System prompt"
        mock_generate_specs.return_value = [{"type": "function", "function": {"name": "test"}}]
        
        # First response with tool calls
        tool_call = MockChatCompletionMessageToolCall(
            id="call_123",
            type="function",
            function=MockChatCompletionMessageToolCallFunction(
                name="TwitterSentimentTool_analyze",
                arguments='{"symbol": "BTC"}'
            )
        )
        
        mock_message1 = MagicMock()
        mock_message1.content = None
        mock_message1.tool_calls = [tool_call]
        
        # Second response with content
        mock_message2 = MagicMock()
        mock_message2.content = "Final response after tool calls"
        mock_message2.tool_calls = None
        
        mock_create.side_effect = [
            MagicMock(choices=[MagicMock(message=mock_message1)]),
            MagicMock(choices=[MagicMock(message=mock_message2)])
        ]
        
        # Set up tool execution result
        mock_execute_tool.return_value = {"result": "Tool executed", "sentiment": 0.8}
        
        # Process a prompt
        result = self.engine.process_prompt("test prompt", "BTC")
        
        # Verify results
        self.assertIn("message", result)
        self.assertEqual(result["message"], "Final response after tool calls")
        self.assertEqual(result["symbol"], "BTC")
        self.assertIn("tool_results", result)
        self.assertIn("TwitterSentimentTool_analyze", result["tool_results"])
        self.assertEqual(result["sentiment"], 0.8)  # The tool result should be added to context
        
        # Verify openai.chat.completions.create was called twice
        self.assertEqual(mock_create.call_count, 2)
        
        # Verify execute_tool_call was called
        mock_execute_tool.assert_called_once_with(tool_call, ANY)
    
    @patch('src.llm_engine.LLMEngine._get_system_prompt')
    @patch('src.llm_engine.LLMEngine._generate_tool_specs')
    @patch('src.llm_engine.openai.chat.completions.create')
    def test_process_prompt_api_error(self, mock_create, mock_generate_specs, mock_get_system):
        """Test handling OpenAI API errors."""
        # Set up mocks
        mock_get_system.return_value = "System prompt"
        mock_generate_specs.return_value = [{"type": "function", "function": {"name": "test"}}]
        
        # Make the API call raise an exception
        mock_create.side_effect = Exception("API error")
        
        # Process a prompt
        result = self.engine.process_prompt("test prompt", "BTC")
        
        # Verify error handling
        self.assertIn("error", result)
        self.assertEqual(result["error"], "API error")
        self.assertEqual(result["symbol"], "BTC")
    
    @patch('src.llm_engine.LLMEngine._generate_tool_specs')
    def test_process_prompt_no_specs(self, mock_generate_specs):
        """Test processing a prompt with no tool specifications."""
        # Return empty specs
        mock_generate_specs.return_value = []
        
        # Process a prompt
        result = self.engine.process_prompt("test prompt", "BTC")
        
        # Verify error handling
        self.assertIn("error", result)
        self.assertEqual(result["error"], "No tool specifications were generated")
        self.assertEqual(result["symbol"], "BTC")
    
    def test_execute_tool_call(self):
        """Test executing a tool call."""
        # Create a partial mock that only mocks _get_tool_instance
        with patch.object(self.engine, '_get_tool_instance') as mock_get_tool:
            # Set up the mock tool
            mock_tool = MagicMock()
            mock_tool.analyze_sentiment.return_value = {"sentiment": 0.8}
            mock_get_tool.return_value = mock_tool
            
            # Create a tool call
            tool_call = MockChatCompletionMessageToolCall(
                id="call_123",
                type="function",
                function=MockChatCompletionMessageToolCallFunction(
                    name="TwitterSentimentTool_analyze_sentiment",
                    arguments='{"symbol": "BTC"}'
                )
            )
            
            # Create context
            context = {"symbol": "BTC", "dry_run": True, "amount": 100.0}
            
            # Execute the tool call
            result = self.engine._execute_tool_call(tool_call, context)
            
            # Verify the result
            self.assertEqual(result, {"sentiment": 0.8})
            
            # Verify the tool was called correctly
            mock_get_tool.assert_called_once_with("TwitterSentimentTool")
            mock_tool.analyze_sentiment.assert_called_once_with(symbol="BTC")
            
            # Verify the context was updated
            self.assertIn("tool_results", context)
            self.assertIn("TwitterSentimentTool_analyze_sentiment", context["tool_results"])
            self.assertEqual(context["tool_results"]["TwitterSentimentTool_analyze_sentiment"], {"sentiment": 0.8})
            self.assertEqual(context["sentiment"], 0.8)
    
    def test_execute_tool_call_unknown_tool(self):
        """Test executing a tool call with an unknown tool."""
        # Create a tool call with an unknown tool
        tool_call = MockChatCompletionMessageToolCall(
            id="call_123",
            type="function",
            function=MockChatCompletionMessageToolCallFunction(
                name="UnknownTool_method",
                arguments='{}'
            )
        )
        
        # Execute the tool call
        result = self.engine._execute_tool_call(tool_call, {})
        
        # Verify the result
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Tool not found: UnknownTool")
    
    def test_execute_tool_call_invalid_function_name(self):
        """Test executing a tool call with an invalid function name."""
        # Create a tool call with an invalid function name (no underscore)
        tool_call = MockChatCompletionMessageToolCall(
            id="call_123",
            type="function",
            function=MockChatCompletionMessageToolCallFunction(
                name="invalid_function_name_format",
                arguments='{}'
            )
        )
        
        # Execute the tool call
        result = self.engine._execute_tool_call(tool_call, {})
        
        # Verify the result
        self.assertIn("error", result)
    
    def test_execute_tool_call_unknown_method(self):
        """Test executing a tool call with an unknown method."""
        # Create a partial mock that only mocks _get_tool_instance
        with patch.object(self.engine, '_get_tool_instance') as mock_get_tool:
            # Set up the mock tool with no analyze_unknown method
            mock_tool = MagicMock(spec=["analyze_sentiment"])
            mock_get_tool.return_value = mock_tool
            
            # Create a tool call with an unknown method
            tool_call = MockChatCompletionMessageToolCall(
                id="call_123",
                type="function",
                function=MockChatCompletionMessageToolCallFunction(
                    name="TwitterSentimentTool_analyze_unknown",
                    arguments='{}'
                )
            )
            
            # Execute the tool call
            result = self.engine._execute_tool_call(tool_call, {})
            
            # Verify the result
            self.assertIn("error", result)
            self.assertEqual(result["error"], "Method not found: TwitterSentimentTool.analyze_unknown")
    
    def test_execute_tool_call_exception(self):
        """Test executing a tool call that raises an exception."""
        # Create a partial mock that only mocks _get_tool_instance
        with patch.object(self.engine, '_get_tool_instance') as mock_get_tool:
            # Set up the mock tool to raise an exception
            mock_tool = MagicMock()
            mock_tool.analyze_sentiment.side_effect = Exception("Tool execution error")
            mock_get_tool.return_value = mock_tool
            
            # Create a tool call
            tool_call = MockChatCompletionMessageToolCall(
                id="call_123",
                type="function",
                function=MockChatCompletionMessageToolCallFunction(
                    name="TwitterSentimentTool_analyze_sentiment",
                    arguments='{"symbol": "BTC"}'
                )
            )
            
            # Execute the tool call
            result = self.engine._execute_tool_call(tool_call, {})
            
            # Verify the result
            self.assertIn("error", result)
            self.assertEqual(result["error"], "Tool execution error")
    
    def test_get_system_prompt(self):
        """Test getting the system prompt."""
        prompt = self.engine._get_system_prompt()
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)  # Should be a non-trivial prompt
        self.assertIn("trading agent", prompt.lower())
    
    def test_serialize_tool_result_success(self):
        """Test successful serialization of tool results."""
        # Test with a simple dictionary
        result = self.engine._serialize_tool_result({"key": "value"})
        self.assertEqual(result, '{"key": "value"}')
        
        # Test with nested structure
        result = self.engine._serialize_tool_result({"nested": {"key": "value"}})
        self.assertEqual(json.loads(result), {"nested": {"key": "value"}})
    
    def test_serialize_tool_result_failure(self):
        """Test serialization failure for tool results."""
        # Create a circular reference that can't be serialized
        circular = {}
        circular["self"] = circular
        
        # Should fall back to string representation
        result = self.engine._serialize_tool_result(circular)
        self.assertIsInstance(result, str)
    
    @patch('src.llm_engine.TradingExecutionTool')
    def test_get_manual_tool_instance(self, mock_trading_tool):
        """Test getting a manual tool instance."""
        # Set up mock
        mock_instance = MagicMock()
        mock_trading_tool.return_value = mock_instance
        
        # Get the tool instance
        result = self.engine._get_manual_tool_instance("TradingExecutionTool")
        
        # Verify the result
        self.assertEqual(result, mock_instance)
        mock_trading_tool.assert_called_once()
    
    def test_get_manual_tool_instance_unknown(self):
        """Test getting an unknown manual tool."""
        result = self.engine._get_manual_tool_instance("UnknownTool")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main() 