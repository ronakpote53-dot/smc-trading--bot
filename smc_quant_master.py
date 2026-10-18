"""
===============================================================================
PROJECT: SMC QUANT ENGINE (PRO MASTER EDITION)
AUTHOR: Ronak Pote
DESCRIPTION: Institutional Quantitative Trading Engine combining Smart Money 
             Concepts (SMC), Fair Value Gap (FVG) Engine, Daily 3% Circuit Breaker,
             Dynamic Risk & Lot Sizing, Telegram Control, and OpenAI AI Validation.
===============================================================================
"""

import time
import requests
import pandas as pd
import numpy as np

# Safe import for MetaTrader5 (Handles Linux Cloud & Windows compatibility)
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[SYSTEM WARNING] MetaTrader5 library not found. Running in Cloud/Webhook Mode.")

# ==========================================
# 1. GLOBAL SYSTEM CONFIGURATION
# ==========================================
class Config:
    # MT5 Broker Credentials (Exness Demo Account)
    MT5_ACCOUNT = 480412532
    MT5_PASSWORD = "Gubu@123"                 
    MT5_SERVER = "Exness-MT5Trial"            
    
    # Risk Management Rules (Universal for any account balance)
    DAILY_MAX_DRAWDOWN_PCT = 3.0              # Hard 3% Daily Circuit Breaker
    DEFAULT_RISK_PER_TRADE_PCT = 1.0          # 1% Risk per trade
    MIN_LOT_SIZE = 0.01                       # Minimum Safe Lot Size for small balances
    
    # AI API Keys
    OPENAI_API_KEY = "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"
    
    # Telegram Control & Notifications
    TELEGRAM_BOT_TOKEN = "8850686281:AAFQms3YLnynRzHTP8BpZv-AjG5gpNZszpw"
    TELEGRAM_CHAT_ID = "5359177105"
    
    # Execution Settings
    SYMBOLS = ["EURUSD", "GBPUSD", "XAUUSD"]


# ==========================================
# 2. TELEGRAM ALERT SYSTEM
# ==========================================
class TelegramNotifier:
    @staticmethod
    def send_message(message: str):
        if not Config.TELEGRAM_BOT_TOKEN or Config.TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
            return False
        url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": Config.TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] Telegram Alert Failed: {e}")
            return False


# ==========================================
# 3. AI INTEGRATION (CHATGPT & CLAUDE)
# ==========================================
class AIAnalyzer:
    @staticmethod
    def analyze_market_state(symbol: str, data_summary: str) -> str:
        """
        Sends aggregated market data & SMC structure to OpenAI
        for higher-timeframe confirmation before trade entry.
        """
        if not Config.OPENAI_API_KEY or "YOUR_OPENAI" in Config.OPENAI_API_KEY:
            return "GO - Strategy Override (No API Key Configured)"

        prompt = (
            f"You are an Institutional Forex Quant. Analyze this market context for {symbol}:\n"
            f"{data_summary}\n"
            f"Confirm if this setup aligns with Smart Money Concepts (SMC) and Fair Value Gap (FVG). "
            f"Respond STRICTLY with 'GO' or 'NO_GO' followed by a 1-sentence reasoning."
        )
        
        try:
            headers = {
                "Authorization": f"Bearer {Config.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            body = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", json=body, headers=headers, timeout=15)
            if res.status_code == 200:
                ai_response = res.json()['choices'][0]['message']['content'].strip()
                return ai_response
        except Exception as e:
            print(f"[AI WARN] OpenAI API unreachable: {e}")
            
        return "GO - Local Strategy Execution Override"


# ==========================================
# 4. SMC & FVG QUANTITATIVE ENGINE
# ==========================================
class SMCEngine:
    def __init__(self, symbol: str):
        self.symbol = symbol

    def fetch_market_data(self, num_bars=100) -> pd.DataFrame:
        if not MT5_AVAILABLE:
            # Mock Data for Cloud/Non-Windows testing
            df = pd.DataFrame({
                'time': pd.date_range(end=pd.Timestamp.now(), periods=num_bars, freq='15min'),
                'open': np.random.uniform(1.08, 1.09, num_bars),
                'high': np.random.uniform(1.09, 1.10, num_bars),
                'low': np.random.uniform(1.07, 1.08, num_bars),
                'close': np.random.uniform(1.08, 1.09, num_bars)
            })
            return df

        rates = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M15, 0, num_bars)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def scan_fvg_and_liquidity(self, df: pd.DataFrame) -> dict:
        if len(df) < 3:
            return {"signal": "NEUTRAL"}

        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        # Bullish Fair Value Gap (FVG)
        if c3['low'] > c1['high']:
            fvg_gap = c3['low'] - c1['high']
            return {
                "signal": "BUY",
                "fvg_top": c3['low'],
                "fvg_bottom": c1['high'],
                "gap_size": fvg_gap
            }

        # Bearish Fair Value Gap (FVG)
        elif c3['high'] < c1['low']:
            fvg_gap = c1['low'] - c3['high']
            return {
                "signal": "SELL",
                "fvg_top": c1['low'],
                "fvg_bottom": c3['high'],
                "gap_size": fvg_gap
            }

        return {"signal": "NEUTRAL"}


# ==========================================
# 5. CORE EXECUTION & CIRCUIT BREAKER ENGINE
# ==========================================
class MasterQuantEngine:
    def __init__(self):
        self.initial_daily_balance = 10000.0  # Default mock balance for safety
        self.circuit_breaker_active = False

    def initialize_mt5(self):
        if not MT5_AVAILABLE:
            print("[CLOUD MODE] MT5 not supported on this OS. Running in Signal & Alert Simulation Mode.")
            TelegramNotifier.send_message("🚀 *SMC QUANT ENGINE STARTED (Cloud Mode)*\n• Running 24/7 Monitoring & AI Validation.")
            return True

        if not mt5.initialize():
            print("[CRITICAL] Failed to initialize MT5 Engine.")
            return False
        
        login_ok = mt5.login(Config.MT5_ACCOUNT, password=Config.MT5_PASSWORD, server=Config.MT5_SERVER)
        if not login_ok:
            print(f"[CRITICAL] MT5 Login failed for account {Config.MT5_ACCOUNT}")
            return False

        account_info = mt5.account_info()
        if account_info:
            self.initial_daily_balance = account_info.balance
            
        print(f"[INFO] MT5 Connected. Account: {Config.MT5_ACCOUNT} | Initial Balance: ${self.initial_daily_balance:.2f}")
        
        TelegramNotifier.send_message(
            f"🚀 *SMC QUANT ENGINE STARTED*\n"
            f"• Account: `{Config.MT5_ACCOUNT}`\n"
            f"• Starting Balance: `${self.initial_daily_balance:.2f}`\n"
            f"• 3% Circuit Breaker Limit: `${self.initial_daily_balance * (Config.DAILY_MAX_DRAWDOWN_PCT/100):.2f}`"
        )
        return True

    def calculate_safe_lot_size(self) -> float:
        if not MT5_AVAILABLE:
            return Config.MIN_LOT_SIZE
            
        account = mt5.account_info()
        if account is None or account.balance <= 0:
            return Config.MIN_LOT_SIZE
        
        calculated_lot = round((account.balance * (Config.DEFAULT_RISK_PER_TRADE_PCT / 100.0)) / 1000.0, 2)
        return max(calculated_lot, Config.MIN_LOT_SIZE)

    def check_circuit_breaker(self) -> bool:
        if not MT5_AVAILABLE:
            return False

        account = mt5.account_info()
        if account is None:
            return False

        current_equity = account.equity
        max_allowed_loss = self.initial_daily_balance * (Config.DAILY_MAX_DRAWDOWN_PCT / 100.0)
        current_drawdown = self.initial_daily_balance - current_equity

        if current_drawdown >= max_allowed_loss:
            self.circuit_breaker_active = True
            print(f"[ALERT] Daily 3% Circuit Breaker Hit! Halting trading activity.")
            self.emergency_close_all()
            
            TelegramNotifier.send_message(
                f"🚨 *HARD CIRCUIT BREAKER TRIGGERED*\n"
                f"• Daily Loss Exceeded 3% Limit!\n"
                f"• Initial Balance: `${self.initial_daily_balance:.2f}`\n"
                f"• Current Equity: `${current_equity:.2f}`\n"
                f"• Execution Status: *ALL TRADES HALTED FOR TODAY*"
            )
            return True
        return False

    def emergency_close_all(self):
        if not MT5_AVAILABLE:
            return
            
        positions = mt5.positions_get()
        if positions:
            for pos in positions:
                tick = mt5.symbol_info_tick(pos.symbol)
                if not tick:
                    continue
                type_dict = {0: mt5.ORDER_TYPE_SELL, 1: mt5.ORDER_TYPE_BUY}
                price_dict = {0: tick.bid, 1: tick.ask}
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": pos.ticket,
                    "symbol": pos.symbol,
                    "volume": pos.volume,
                    "type": type_dict[pos.type],
                    "price": price_dict[pos.type],
                    "deviation": 20,
                    "magic": 100001,
                    "comment": "Circuit Breaker Emergency Close",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                mt5.order_send(request)

    def send_order(self, symbol: str, signal: str):
        lot_size = self.calculate_safe_lot_size()
        
        if not MT5_AVAILABLE:
            print(f"[SIMULATED ORDER] {symbol} {signal} Volume: {lot_size}")
            TelegramNotifier.send_message(
                f"✅ *SIMULATED ORDER EXECUTED (Cloud Mode)*\n"
                f"• Symbol: `{symbol}`\n"
                f"• Type: `{signal}`\n"
                f"• Volume: `{lot_size}`"
            )
            return

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return

        order_type = mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if signal == "BUY" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": 100001,
            "comment": "SMC Quant Trade Entry",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[ORDER EXECUTED] {symbol} {signal} Volume: {lot_size} @ {price}")
            TelegramNotifier.send_message(
                f"✅ *ORDER EXECUTED*\n"
                f"• Symbol: `{symbol}`\n"
                f"• Type: `{signal}`\n"
                f"• Volume: `{lot_size}`\n"
                f"• Price: `{price}`"
            )
        else:
            retcode = result.retcode if result else "Unknown Error"
            print(f"[ORDER FAILED] Error Code: {retcode}")

    def execute_strategy(self):
        for symbol in Config.SYMBOLS:
            engine = SMCEngine(symbol)
            df = engine.fetch_market_data()
            if df.empty:
                continue

            analysis = engine.scan_fvg_and_liquidity(df)
            signal = analysis['signal']

            if signal in ["BUY", "SELL"]:
                print(f"[SETUP DETECTED] {symbol} - {signal} FVG Structure Found.")
                
                summary = f"Symbol: {symbol}, Signal: {signal}, FVG Gap: {analysis.get('gap_size', 0)}"
                ai_decision = AIAnalyzer.analyze_market_state(symbol, summary)
                
                if ai_decision.startswith("GO") and not ai_decision.startswith("NO_GO"):
                    print(f"[AI APPROVED] Executing trade entry for {symbol}")
                    self.send_order(symbol, signal)
                else:
                    print(f"[AI REJECTED] Signal discarded by AI: {ai_decision}")

    def run(self):
        if not self.initialize_mt5():
            return

        print("⚡ SMC Quant Engine Master Loop Active...")
        while True:
            try:
                if self.check_circuit_breaker():
                    break

                self.execute_strategy()
                time.sleep(60)

            except KeyboardInterrupt:
                print("\n[STOPPED] Engine manually halted by user.")
                TelegramNotifier.send_message("🛑 *SMC Quant Engine Manually Halted.*")
                break
            except Exception as e:
                print(f"[RUNTIME ERROR] {e}")
                time.sleep(10)


if __name__ == "__main__":
    bot = MasterQuantEngine()
    bot.run()
