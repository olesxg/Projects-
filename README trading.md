# Crypto Analysis Trading Bot

A cryptocurrency trading bot that monitors multiple trading pairs on Binance, analyzes price movements, and sends alerts via Telegram when prices approach local extremes.

## Features

- **Real-time Monitoring**: Tracks 20 major cryptocurrency pairs including BTC, ETH, BNB, and more
- **Technical Analysis**: Identifies local price extremes (highs and lows)
- **Alert System**: Sends notifications via Telegram when prices approach significant levels
- **Trading Signals**: Provides potential entry points for long and short positions
- **Customizable Parameters**: Easily adjust timeframes, lookback periods, and threshold percentages

## Requirements

- Python 3.7+
- Binance account with API keys
- Telegram bot token and chat ID

## Installation

1. Clone this repository:
   ```
   git clone [repository-url]
   cd Trading-Bot
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

## Configuration

1. Create a `.env` file in the project directory with the following variables:
   ```
   BINANCE_API_KEY=your_binance_api_key
   BINANCE_API_SECRET=your_binance_api_secret
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```

2. To get these credentials:
   - **Binance API**: Generate API keys from your Binance account settings
   - **Telegram Bot**: Create a bot via [@BotFather](https://t.me/botfather) and get the token
   - **Chat ID**: Start a chat with your bot and get the chat ID from https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates

## Usage

Run the bot:
```
python Trading_bot.py
```

The bot will:
1. Connect to Binance and fetch historical data for the configured trading pairs
2. Analyze price movements to identify local extremes
3. Send alerts via Telegram when prices approach these extremes
4. Continue monitoring at regular intervals

## Customization

You can modify the following parameters in the `CryptoAnalysisBot` class:
- `pairs`: List of cryptocurrency trading pairs to monitor
- `timeframe`: Chart timeframe for analysis (default: '4h')
- `lookback_days`: Number of days to look back for historical data (default: 4)
- `threshold_percentage`: Percentage distance to consider price "near" an extreme (default: 3%)

## Logging

The bot logs its activity to both the console and a file named `crypto_bot.log`. Check this file for detailed information about the bot's operation and any errors that occur.

## Disclaimer

This bot is for informational purposes only and does not constitute financial advice. Always conduct your own research before making trading decisions. Use at your own risk.

## License

[Your License Information]