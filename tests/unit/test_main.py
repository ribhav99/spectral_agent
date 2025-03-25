import unittest
from unittest.mock import patch, MagicMock
import sys
import io
from src.main import parse_arguments, main

class TestMain(unittest.TestCase):
    """Test the main module."""
    
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
    
    def test_parse_arguments_defaults(self):
        """Test parse_arguments with default values."""
        with patch('sys.argv', ['main.py']):
            args = parse_arguments()
            self.assertIsNone(args.prompt)
            self.assertEqual(args.symbol, "BTC")
            self.assertFalse(args.dry_run)
            self.assertFalse(args.interactive)
            self.assertFalse(args.debug)
            self.assertEqual(args.amount, 0.01)
    
    def test_parse_arguments_with_values(self):
        """Test parse_arguments with specified values."""
        with patch('sys.argv', [
            'main.py',
            '--prompt', 'Test prompt',
            '--symbol', 'ETH',
            '--dry-run',
            '--interactive',
            '--debug',
            '--amount', '100.0'
        ]):
            args = parse_arguments()
            self.assertEqual(args.prompt, "Test prompt")
            self.assertEqual(args.symbol, "ETH")
            self.assertTrue(args.dry_run)
            self.assertTrue(args.interactive)
            self.assertTrue(args.debug)
            self.assertEqual(args.amount, 100.0)
    
    @patch('src.main.get_user_input')
    @patch('src.main.display_results')
    @patch('src.main.LLMEngine')
    @patch('src.main.config.display_config_info')
    def test_main_interactive_mode(self, mock_display_config, mock_llm_engine_class, mock_display_results, mock_get_user_input):
        """Test main function in interactive mode."""
        # Mock command line arguments
        with patch('sys.argv', ['main.py', '--interactive']):
            # Mock user input
            mock_get_user_input.return_value = {
                "prompt": "Test prompt",
                "symbol": "ETH",
                "dry_run": True,
                "amount": 50.0
            }
            
            # Mock LLMEngine
            mock_llm_engine = MagicMock()
            mock_llm_engine_class.return_value = mock_llm_engine
            mock_llm_engine.process_prompt.return_value = {"status": "success"}
            
            # Call main function
            main()
            
            # Verify function calls
            mock_display_config.assert_called_once()
            mock_get_user_input.assert_called_once()
            mock_llm_engine.process_prompt.assert_called_once_with(
                "Test prompt", "ETH", dry_run=True, amount=50.0
            )
            mock_display_results.assert_called_once_with({"status": "success"})
    
    @patch('src.main.display_results')
    @patch('src.main.LLMEngine')
    @patch('src.main.config.display_config_info')
    def test_main_command_line_mode(self, mock_display_config, mock_llm_engine_class, mock_display_results):
        """Test main function in command line mode."""
        # Mock command line arguments
        with patch('sys.argv', [
            'main.py',
            '--prompt', 'Test prompt',
            '--symbol', 'ETH',
            '--dry-run',
            '--amount', '50.0'
        ]):
            # Mock LLMEngine
            mock_llm_engine = MagicMock()
            mock_llm_engine_class.return_value = mock_llm_engine
            mock_llm_engine.process_prompt.return_value = {"status": "success"}
            
            # Call main function
            main()
            
            # Verify function calls
            mock_display_config.assert_called_once()
            mock_llm_engine.process_prompt.assert_called_once_with(
                'Test prompt', 'ETH', dry_run=True, amount=50.0
            )
            mock_display_results.assert_called_once_with({"status": "success"})
    
    @patch('src.main.display_results')
    @patch('src.main.LLMEngine')
    @patch('src.main.config.display_config_info')
    def test_main_large_amount_warning(self, mock_display_config, mock_llm_engine_class, mock_display_results):
        """Test main function with a large amount."""
        # Mock command line arguments
        with patch('sys.argv', [
            'main.py',
            '--prompt', 'Test prompt',
            '--amount', '1000.0'  # Large amount
        ]):
            # Mock LLMEngine
            mock_llm_engine = MagicMock()
            mock_llm_engine_class.return_value = mock_llm_engine
            mock_llm_engine.process_prompt.return_value = {"status": "success"}
            
            # Call main function
            main()
            
            # Check warning message
            output = self.get_output()
            self.assertIn("WARNING: Trading with a large amount ($1000.0)", output)
            
            # Verify function calls
            mock_llm_engine.process_prompt.assert_called_once()
            mock_display_results.assert_called_once()
    
    @patch('src.main.display_results')
    @patch('src.main.LLMEngine')
    @patch('src.main.config.display_config_info')
    def test_main_small_amount_note(self, mock_display_config, mock_llm_engine_class, mock_display_results):
        """Test main function with a small amount."""
        # Mock command line arguments
        with patch('sys.argv', [
            'main.py',
            '--prompt', 'Test prompt',
            '--amount', '0.05'  # Small amount
        ]):
            # Mock LLMEngine
            mock_llm_engine = MagicMock()
            mock_llm_engine_class.return_value = mock_llm_engine
            mock_llm_engine.process_prompt.return_value = {"status": "success"}
            
            # Call main function
            main()
            
            # Check info message
            output = self.get_output()
            self.assertIn("Note: Trading with a small amount ($0.05)", output)
            
            # Verify function calls
            mock_llm_engine.process_prompt.assert_called_once()
            mock_display_results.assert_called_once()
    
    @patch('src.main.display_results')
    @patch('src.main.LLMEngine')
    @patch('src.main.config.display_config_info')
    def test_main_no_prompt_error(self, mock_display_config, mock_llm_engine_class, mock_display_results):
        """Test main function with no prompt provided."""
        # Mock command line arguments
        with patch('sys.argv', [
            'main.py',  # No prompt provided
        ]):
            # Call main function (should exit)
            with self.assertRaises(SystemExit):
                main()
            
            # Check error message
            output = self.get_output()
            self.assertIn("Error: No prompt provided", output)
            
            # Verify LLMEngine was not called
            mock_llm_engine_class.assert_not_called()
            mock_display_results.assert_not_called()
    
    @patch('src.main.display_results')
    @patch('src.main.LLMEngine')
    @patch('src.main.config.display_config_info')
    def test_main_llm_engine_error(self, mock_display_config, mock_llm_engine_class, mock_display_results):
        """Test main function with LLMEngine error."""
        # Mock command line arguments
        with patch('sys.argv', [
            'main.py',
            '--prompt', 'Test prompt',
        ]):
            # Mock LLMEngine to raise an exception
            mock_llm_engine = MagicMock()
            mock_llm_engine_class.return_value = mock_llm_engine
            mock_llm_engine.process_prompt.side_effect = Exception("Test error")
            
            # Call main function
            main()
            
            # Check error message
            output = self.get_output()
            self.assertIn("Error: Test error", output)
            
            # Verify display_results was not called
            mock_display_results.assert_not_called()
    
    @patch('src.main.display_results')
    @patch('src.main.LLMEngine')
    @patch('src.main.config.display_config_info')
    def test_main_llm_engine_no_result(self, mock_display_config, mock_llm_engine_class, mock_display_results):
        """Test main function with no result from LLMEngine."""
        # Mock command line arguments
        with patch('sys.argv', [
            'main.py',
            '--prompt', 'Test prompt',
        ]):
            # Mock LLMEngine to return None
            mock_llm_engine = MagicMock()
            mock_llm_engine_class.return_value = mock_llm_engine
            mock_llm_engine.process_prompt.return_value = None
            
            # Call main function
            main()
            
            # Check error message
            output = self.get_output()
            self.assertIn("Error: Failed to get results from LLM engine", output)
            
            # Verify display_results was not called
            mock_display_results.assert_not_called()
    
    @patch('src.main.logging')
    @patch('src.main.display_results')
    @patch('src.main.LLMEngine')
    @patch('src.main.config.display_config_info')
    def test_main_debug_mode(self, mock_display_config, mock_llm_engine_class, mock_display_results, mock_logging):
        """Test main function in debug mode."""
        # Mock command line arguments
        with patch('sys.argv', [
            'main.py',
            '--prompt', 'Test prompt',
            '--debug'
        ]):
            # Mock logger dictionary
            mock_logger_dict = {"src.module1": MagicMock(), "src.module2": MagicMock(), "other.module": MagicMock()}
            mock_logging.root.manager.loggerDict = mock_logger_dict
            
            # Mock LLMEngine
            mock_llm_engine = MagicMock()
            mock_llm_engine_class.return_value = mock_llm_engine
            mock_llm_engine.process_prompt.return_value = {"status": "success"}
            
            # Call main function
            main()
            
            # Verify logging was configured correctly
            self.assertEqual(mock_logging.getLogger.call_count, 3)  # src.module1, src.module2, openai
            mock_logging.getLogger.assert_any_call("src.module1")
            mock_logging.getLogger.assert_any_call("src.module2")
            mock_logging.getLogger.assert_any_call("openai")
            
            # Verify debug level was set
            mock_logging.getLogger.return_value.setLevel.assert_called_with(mock_logging.DEBUG)


if __name__ == "__main__":
    unittest.main() 