import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
import telegram
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from dotenv import load_dotenv
import sys
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import platform

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crypto_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CryptoAnalysisBot:
    def __init__(self):
        # Initialize Binance client
        self.binance_client = Client(
            os.getenv('BINANCE_API_KEY'),
            os.getenv('BINANCE_API_SECRET'),
        )
        
        # Initialize Telegram bot
        self.telegram_bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # Trading pairs to monitor
        self.pairs = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT',
            'XRPUSDT', 'DOTUSDT', 'UNIUSDT', 'LINKUSDT', 'SOLUSDT',
            'TRXUSDT', 'TONUSDT', 'MATICUSDT', 'LTCUSDT', 'AVAXUSDT',
            'ATOMUSDT', 'APEUSDT', 'SHIBUSDT', 'APTUSDT', 'OPUSDT'
        ]
        
        # Analysis parameters
        self.timeframe = '4h'
        self.lookback_days = 4
        self.threshold_percentage = 3
        
        # Message queue
        self.message_queue = asyncio.Queue()

    def get_historical_data(self, symbol, interval='1h', lookback_days=4):
        """Retrieve historical OHLCV data from Binance"""
        try:
            start_time = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
            
            klines = self.binance_client.get_klines(
                symbol=symbol,
                interval=interval,
                startTime=start_time,
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None

    def find_local_extremes(self, df):
        """Find local maximum and minimum prices"""
        if df is None or len(df) < 2:
            return None, None
            
        try:
            local_max = df['high'].max()
            local_min = df['low'].min()
            return local_max, local_min
            
        except Exception as e:
            logger.error(f"Error calculating local extremes: {str(e)}")
            return None, None

    def is_price_near_extreme(self, current_price, extreme_price, threshold_percentage):
        """Check if current price is near local extreme"""
        if current_price is None or extreme_price is None:
            return False
            
        difference_percentage = abs((current_price - extreme_price) / extreme_price * 100)
        return difference_percentage <= threshold_percentage

    async def send_telegram_alert(self, message: str) -> bool:
        """Send alert message via Telegram with retry logic"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                await self.telegram_bot.send_message(
                    chat_id=self.telegram_chat_id,
                    text=message,
                    parse_mode='HTML'
                )
                logger.info("Telegram alert sent successfully")
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to send Telegram alert after {max_retries} attempts: {str(e)}")
                    return False
                logger.warning(f"Telegram alert attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
        return False

    async def analyze_pair(self, symbol):
        """Analyze a single trading pair"""
        try:
            df = self.get_historical_data(
                symbol,
                self.timeframe,
                self.lookback_days
            )
            
            if df is None or df.empty:
                logger.warning(f"No data available for {symbol}")
                return
                
            current_price = float(df['close'].iloc[-1])
            local_max, local_min = self.find_local_extremes(df)
            
            near_max = self.is_price_near_extreme(
                current_price,
                local_max,
                self.threshold_percentage
            )
            
            near_min = self.is_price_near_extreme(
                current_price,
                local_min,
                self.threshold_percentage
            )
            
            if near_max or near_min:
                current_price_formatted = f"${current_price:,.2f}"
                local_max_formatted = f"${local_max:,.2f}"
                local_min_formatted = f"${local_min:,.2f}"

                max_percentage = ((current_price - local_max) / local_max) * 100
                min_percentage = ((current_price - local_min) / local_min) * 100
                
                message = (
                    f"🚨 {symbol} Alert 🚨\n\n"
                    f"📊 Current Price: {current_price_formatted}\n"
                    f"📈 Local High: {local_max_formatted}\n"
                    f"📉 Local Low: {local_min_formatted}\n\n"
                )
                
                if near_max:
                    message += (
                        f"⚠️ Price is approaching the local high(LONG!🟢)\n"
                        f"📊 Distance to the high: {abs(max_percentage):.2f}%\n"
                    )
                if near_min:
                    message += (
                        f"⚠️ Price is approaching the local low!(SHORT!🔴)\n"
                        f"📊 Distance to the low: {abs(min_percentage):.2f}%\n"
                    )
                
                await self.send_telegram_alert(message)
                
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")

    async def run(self):
        """Main bot loop"""
        logger.info("Starting Crypto Analysis Bot...")
        
        while True:
            try:
                for pair in self.pairs:
                    logger.info(f"Analyzing {pair}...")
                    await self.analyze_pair(pair)
                    await asyncio.sleep(1)
                
                logger.info("Analysis round completed. Waiting for next round...")
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(60)

async def main():
    # Set up the event loop policy for Windows
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    required_env_vars = [
        'BINANCE_API_KEY',
        'BINANCE_API_SECRET',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        if not os.path.exists('.env'):
            with open('.env', 'w') as f:
                f.write("\n".join(f"{var}=your_{var.lower()}" for var in required_env_vars))
            logger.info("Created .env file template. Please fill in your API keys and tokens.")
        sys.exit(1)
    
    try:
        bot = CryptoAnalysisBot()
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
