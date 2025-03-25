import unittest
from unittest.mock import patch, MagicMock
import os
import io
import sys

from src import config

class TestConfig(unittest.TestCase):
    """Test the config module."""
    
    def setUp(self):
        """Set up test environment."""
        # Save original environment variables
        self.orig_env = os.environ.copy()
        
        # Redirect stdout to capture print statements
        self.held_output = io.StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.held_output
        
        # Set test environment variables
        os.environ["OPENAI_API_KEY"] = "test_openai_key"
        os.environ["TWITTER_API_KEY"] = "test_twitter_key"
        os.environ["HYPERLIQUID_PRIVATE_KEY"] = "test_hyperliquid_key"
        os.environ["DEFAULT_POSITION_SIZE"] = "0.05"
        os.environ["DEFAULT_STOP_LOSS_PERCENT"] = "0.03"
        os.environ["HYPERLIQUID_API_TESTNET"] = "https://test-api.example.com"
        os.environ["HYPERLIQUID_API_MAINNET"] = "https://main-api.example.com"
        os.environ["ENVIRONMENT"] = "test"
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["USE_REAL_API"] = "false"
    
    def tearDown(self):
        """Tear down test environment."""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.orig_env)
        
        # Restore stdout
        sys.stdout = self.original_stdout
    
    def test_environment_variables_loaded(self):
        """Test that environment variables are correctly loaded."""
        # Reload the module to apply our test environment variables
        reload_module(config)
        
        # Check each config variable
        self.assertEqual(config.OPENAI_API_KEY, "test_openai_key")
        self.assertEqual(config.TWITTER_API_KEY, "test_twitter_key")
        self.assertEqual(config.HYPERLIQUID_PRIVATE_KEY, "test_hyperliquid_key")
        self.assertEqual(config.DEFAULT_POSITION_SIZE, 0.05)
        self.assertEqual(config.DEFAULT_STOP_LOSS_PERCENT, 0.03)
        self.assertEqual(config.HYPERLIQUID_API_TESTNET, "https://test-api.example.com")
        self.assertEqual(config.HYPERLIQUID_API_MAINNET, "https://main-api.example.com")
        self.assertEqual(config.ENVIRONMENT, "test")
        self.assertEqual(config.LOG_LEVEL, "DEBUG")
        self.assertEqual(config.USE_REAL_API, False)
    
    def test_environment_variables_defaults(self):
        """Test that default values are used when environment variables are not set."""
        # Clear specific environment variables to test defaults
        for key in ["DEFAULT_POSITION_SIZE", "DEFAULT_STOP_LOSS_PERCENT", "ENVIRONMENT", 
                   "LOG_LEVEL", "USE_REAL_API", "HYPERLIQUID_API_TESTNET", "HYPERLIQUID_API_MAINNET"]:
            if key in os.environ:
                del os.environ[key]
        
        # Reload the module to apply changes
        reload_module(config)
        
        # Check defaults
        self.assertEqual(config.DEFAULT_POSITION_SIZE, 0.01)
        self.assertEqual(config.DEFAULT_STOP_LOSS_PERCENT, 0.02)
        self.assertEqual(config.ENVIRONMENT, "development")
        self.assertEqual(config.LOG_LEVEL, "INFO")
        self.assertEqual(config.USE_REAL_API, True)
        self.assertEqual(config.HYPERLIQUID_API_TESTNET, "https://api.hyperliquid-testnet.xyz")
        self.assertEqual(config.HYPERLIQUID_API_MAINNET, "https://api.hyperliquid.xyz")
    
    def test_display_config_info_development(self):
        """Test display_config_info in development environment."""
        # Set environment to development
        os.environ["ENVIRONMENT"] = "development"
        reload_module(config)
        
        # Call the function
        config.display_config_info()
        
        # Get the output
        output = self.held_output.getvalue()
        
        # Verify output contains expected information
        self.assertIn("Configuration:", output)
        self.assertIn("- Environment: development", output)
        self.assertIn("- Log Level: DEBUG", output)
        self.assertIn("- Hyperliquid API: Disabled (using synthetic data)", output)
        self.assertIn("- OpenAI API: Configured", output)
        self.assertIn("- Private Key: Configured", output)
        self.assertIn("- Position Size: 5.0%", output)
        self.assertIn("- Stop Loss: 3.0%", output)
    
    def test_display_config_info_production(self):
        """Test display_config_info in production environment."""
        # Set environment to production
        os.environ["ENVIRONMENT"] = "production"
        reload_module(config)
        
        # Call the function
        config.display_config_info()
        
        # Get the output
        output = self.held_output.getvalue()
        
        # In production, it should display nothing
        self.assertEqual(output, "")
    
    def test_api_disabled(self):
        """Test USE_REAL_API with various values."""
        # Test with "false"
        os.environ["USE_REAL_API"] = "false"
        reload_module(config)
        self.assertEqual(config.USE_REAL_API, False)
        
        # Test with "False"
        os.environ["USE_REAL_API"] = "False"
        reload_module(config)
        self.assertEqual(config.USE_REAL_API, False)
        
        # Test with "true"
        os.environ["USE_REAL_API"] = "true"
        reload_module(config)
        self.assertEqual(config.USE_REAL_API, True)
        
        # Test with "True"
        os.environ["USE_REAL_API"] = "True"
        reload_module(config)
        self.assertEqual(config.USE_REAL_API, True)


def reload_module(module):
    """Reload a module to apply changed environment variables."""
    import importlib
    importlib.reload(module)


if __name__ == "__main__":
    unittest.main() 