# LLM-Powered Trading Agent

An LLM-driven trading agent that interacts with Hyperliquid to execute trades based on various tools. The LLM acts as the central decision-making engine, dynamically selecting tools based on user context and need.

## Key Features

- **Advanced LLM Agent Architecture**: Uses OpenAI's function calling to intelligently select and execute the right tools at the right time.
- **Dynamic Tool Selection**: LLM dynamically decides which tools to use based on the specific context and requirements.
- **Modular Tools System**: Tools like Twitter sentiment analysis, market data fetcher, decision trees, and trade execution provide insights and actions.
- **Fully Agent-Driven**: The LLM maintains state and chains multiple tools together to achieve the user's goals.
- **Hyperliquid Trading Execution**: Executes trades programmatically on the Hyperliquid Testnet.
- **No API Keys Required for Twitter**: Uses snscrape to analyze Twitter sentiment without API keys or rate limits.

## Architecture

The project follows a modern AI agent architecture with the following components:

- **LLM Engine**: Core agent that dynamically decides which tools to call based on context.
- **Tool Specification System**: Automatically generates OpenAI function descriptions from tool classes.
- **Tools**: Modular components for data collection, analysis, and execution:
  - Twitter Sentiment Analysis: Analyzes crypto sentiment on Twitter using snscrape.
  - Market Data: Fetches live trading data from Hyperliquid.
  - Decision Tree: Applies ML models to trading decisions.
  - Decision: Makes a final LONG/SHORT recommendation.
  - Trading Execution: Executes trades on Hyperliquid with risk management.

## Setup & Installation

1. **Clone Repo**
   ```bash
   git clone https://github.com/yourusername/llm-trading-agent.git
   cd llm-trading-agent
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up API Keys**
   Create a `.env` file in the root directory with your API keys:
   ```
   OPENAI_API_KEY=your_key_here
   ENVIRONMENT=development
   ```

   **Hyperliquid Setup:**
   - For detailed instructions on setting up Hyperliquid API access, see [HYPERLIQUID_SETUP.md](HYPERLIQUID_SETUP.md)
   - The agent can run in synthetic data mode without API access by setting `USE_REAL_API=false` in your `.env` file

4. **Install snscrape**
   For Twitter sentiment analysis, make sure snscrape is properly installed:
   ```bash
   pip install git+https://github.com/JustAnotherArchivist/snscrape.git
   ```

5. **Run the Agent**
   ```bash
   # Run in interactive mode
   python -m src.main --interactive
   
   # Run with specific parameters
   python -m src.main --prompt "trade using sentiment" --symbol BTC --dry-run
   ```

## Example Usage

```bash
# Analyze sentiment without executing trade
python -m src.main --prompt "analyze sentiment for BTC" --symbol BTC --dry-run

# Trade based on market data for ETH (will execute if not in dry-run mode)
python -m src.main --prompt "execute a trade based on price action" --symbol ETH --dry-run

# Comprehensive analysis and trading for SOL
python -m src.main --prompt "analyze the market and execute a trade if conditions are favorable" --symbol SOL --dry-run

# Run in interactive mode
python -m src.main --interactive
```

## Agent Workflow

1. **User Input**: User provides a natural language request
2. **LLM Analysis**: LLM analyzes the request and determines which tools to call and in what order
3. **Dynamic Tool Execution**: LLM executes a sequence of tools, using the output of one tool as input to another
   - For example: Market Data → Decision Tree → Decision → Trading Execution
4. **Contextual Decision Making**: LLM maintains context throughout the interaction, making informed decisions at each step
5. **Results**: The final results (analysis or trade execution) are returned to the user

## Technical Implementation

The agent uses OpenAI's function calling API to implement the following pattern:

1. **Tool Discovery**: Automatically extracts tool parameters and descriptions from Python classes
2. **Tool Selection**: LLM selects the appropriate tool based on context and user request
3. **Tool Execution**: The system executes the tools and feeds results back to the LLM
4. **Chained Reasoning**: LLM maintains context across multiple tool calls to achieve the user's goal

## Disclaimer

This project is for educational purposes only. Use at your own risk. Trading cryptocurrency involves significant risk and you can lose your money. 