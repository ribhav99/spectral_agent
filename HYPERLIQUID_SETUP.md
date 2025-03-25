# Setting Up Hyperliquid API Access

This document explains how to set up and configure Hyperliquid API access for the LLM Trading Agent.

## Hyperliquid Account Setup

1. **Create a Hyperliquid Account**
   - Visit [Hyperliquid](https://app.hyperliquid.xyz) and connect your wallet
   - For testing, use the [Hyperliquid Testnet](https://testnet.hyperliquid.xyz)

2. **Get Testnet ETH**
   - You'll need testnet ETH to interact with the Hyperliquid testnet
   - Use a faucet like [Arbitrum Goerli Faucet](https://faucet.quicknode.com/arbitrum/goerli)

3. **Generate a Private Key**
   - You can use an existing wallet's private key or generate a new one
   - Make sure you use a key that you're comfortable using for testing purposes
   - Never share your private key or use a production key for testing

## Configure the Agent

### Using Environment Variables

1. Create a `.env` file in the project root (or copy and rename `.env.example`):
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   HYPERLIQUID_PRIVATE_KEY=your_hyperliquid_private_key_here
   ```

2. Replace `your_hyperliquid_private_key_here` with your actual private key (starts with 0x)

3. You can optionally override API endpoints:
   ```
   HYPERLIQUID_API_TESTNET=https://api.hyperliquid-testnet.xyz/v1
   HYPERLIQUID_API_MAINNET=https://api.hyperliquid.xyz/v1
   ```

## Testing the Connection

1. Run the agent with the API configured:
   ```bash
   # Test in interactive mode
   python -m src.main --interactive
   ```

2. You should see configuration information showing your API is configured:
   ```
   Configuration:
   - Environment: development
   - Log Level: INFO
   - Hyperliquid API: Enabled
   - Hyperliquid Testnet API: https://api.hyperliquid-testnet.xyz/v1
   - OpenAI API: Configured
   - Private Key: Configured
   - Position Size: 1.0%
   - Stop Loss: 2.0%
   ```

3. Try fetching market data:
   ```
   > analyze ETH market data
   ```

4. If the connection is working, you should see real market data from Hyperliquid.

## Switching Between Real and Synthetic Data

If you want to develop without making real API calls, you can use synthetic data:

1. Add this to your `.env` file:
   ```
   USE_REAL_API=false
   ```

2. Now the agent will use synthetic data instead of making real API calls.

## Troubleshooting

1. **API Connection Issues**
   - Check that your internet connection is working
   - Verify API endpoints are correct
   - Make sure you're using the testnet URLs for testnet and mainnet URLs for mainnet

2. **Authentication Issues**
   - Verify your private key is correctly formatted (should start with 0x)
   - Try a different wallet/key to rule out permissions issues

3. **Rate Limiting**
   - If you're making too many requests, you might be rate limited
   - Add delays between requests or reduce the frequency of API calls

4. **Logging Issues**
   - Run with debug mode to see more information:
     ```bash
     python -m src.main --interactive --debug
     ```

## Security Considerations

- Never commit your private keys to Git
- Use environment variables that are in .gitignore
- Consider using a separate wallet with limited funds for testing
- For production, use proper key management and secure storage 