"""
台股即時報價查詢系統
Taiwan Stock Quote & Technical Analysis
"""
import os
from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ta

app = Flask(__name__)

# 常用股票清單
POPULAR_STOCKS = {
    "2330": "台積電",
    "2317": "鴻海",
    "2454": "聯發科",
    "2308": "台達電",
    "2382": "廣達",
    "2881": "富邦金",
    "2882": "國泰金",
    "2891": "中信金",
    "0050": "元大台灣50",
    "0056": "元大高股息",
    "00878": "國泰永續高股息",
    "00919": "群益台灣精選高息",
    "00929": "復華台灣科技優息",
}


def get_stock_symbol(code: str) -> str:
    """轉換股票代號為 Yahoo Finance 格式"""
    code = code.strip()
    if code.endswith('.TW') or code.endswith('.TWO'):
        return code
    # 預設為上市股票
    return f"{code}.TW"


def fetch_stock_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """取得股票歷史資料"""
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        if df.empty:
            # 嘗試上櫃股票
            symbol_two = symbol.replace('.TW', '.TWO')
            stock = yf.Ticker(symbol_two)
            df = stock.history(period=period)
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()


def calculate_technical_indicators(df: pd.DataFrame) -> dict:
    """計算技術指標"""
    if df.empty or len(df) < 26:
        return {}
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    # 移動平均線
    ma5 = close.rolling(window=5).mean()
    ma10 = close.rolling(window=10).mean()
    ma20 = close.rolling(window=20).mean()
    ma60 = close.rolling(window=60).mean() if len(close) >= 60 else pd.Series([None] * len(close))
    ma120 = close.rolling(window=120).mean() if len(close) >= 120 else pd.Series([None] * len(close))
    ma240 = close.rolling(window=240).mean() if len(close) >= 240 else pd.Series([None] * len(close))
    
    # KD 指標 (隨機指標)
    stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close, window=9, smooth_window=3)
    k_values = stoch.stoch()
    d_values = stoch.stoch_signal()
    
    # MACD
    macd = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd.macd()
    signal_line = macd.macd_signal()
    macd_hist = macd.macd_diff()
    
    # RSI
    rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi()
    
    # 乖離率 (BIAS)
    bias5 = ((close - ma5) / ma5 * 100).round(2)
    bias10 = ((close - ma10) / ma10 * 100).round(2)
    bias20 = ((close - ma20) / ma20 * 100).round(2)
    
    # 布林通道
    bollinger = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    bb_upper = bollinger.bollinger_hband()
    bb_middle = bollinger.bollinger_mavg()
    bb_lower = bollinger.bollinger_lband()
    
    # 威廉指標
    williams = ta.momentum.WilliamsRIndicator(high=high, low=low, close=close, lbp=14).williams_r()
    
    # 準備回傳資料 (轉換為 list 給前端)
    dates = [d.strftime('%Y-%m-%d') for d in df.index]
    
    return {
        "dates": dates,
        "ohlc": {
            "open": df['Open'].round(2).tolist(),
            "high": df['High'].round(2).tolist(),
            "low": df['Low'].round(2).tolist(),
            "close": df['Close'].round(2).tolist(),
        },
        "volume": (df['Volume'] / 1000).round(0).tolist(),  # 轉為張
        "ma": {
            "ma5": [None if pd.isna(x) else round(x, 2) for x in ma5],
            "ma10": [None if pd.isna(x) else round(x, 2) for x in ma10],
            "ma20": [None if pd.isna(x) else round(x, 2) for x in ma20],
            "ma60": [None if pd.isna(x) else round(x, 2) for x in ma60],
            "ma120": [None if pd.isna(x) else round(x, 2) for x in ma120],
            "ma240": [None if pd.isna(x) else round(x, 2) for x in ma240],
        },
        "kd": {
            "k": [None if pd.isna(x) else round(x, 2) for x in k_values],
            "d": [None if pd.isna(x) else round(x, 2) for x in d_values],
        },
        "macd": {
            "macd": [None if pd.isna(x) else round(x, 2) for x in macd_line],
            "signal": [None if pd.isna(x) else round(x, 2) for x in signal_line],
            "histogram": [None if pd.isna(x) else round(x, 2) for x in macd_hist],
        },
        "rsi": [None if pd.isna(x) else round(x, 2) for x in rsi],
        "bias": {
            "bias5": [None if pd.isna(x) else x for x in bias5],
            "bias10": [None if pd.isna(x) else x for x in bias10],
            "bias20": [None if pd.isna(x) else x for x in bias20],
        },
        "bollinger": {
            "upper": [None if pd.isna(x) else round(x, 2) for x in bb_upper],
            "middle": [None if pd.isna(x) else round(x, 2) for x in bb_middle],
            "lower": [None if pd.isna(x) else round(x, 2) for x in bb_lower],
        },
        "williams": [None if pd.isna(x) else round(x, 2) for x in williams],
    }


def get_stock_info(symbol: str) -> dict:
    """取得股票基本資訊"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # 取得即時報價
        hist = stock.history(period="5d")
        if hist.empty:
            symbol_two = symbol.replace('.TW', '.TWO')
            stock = yf.Ticker(symbol_two)
            info = stock.info
            hist = stock.history(period="5d")
        
        if hist.empty:
            return None
        
        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100
        
        return {
            "symbol": symbol.replace('.TW', '').replace('.TWO', ''),
            "name": info.get('longName', info.get('shortName', symbol)),
            "current_price": round(current_price, 2),
            "prev_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "open": round(hist['Open'].iloc[-1], 2),
            "high": round(hist['High'].iloc[-1], 2),
            "low": round(hist['Low'].iloc[-1], 2),
            "volume": int(hist['Volume'].iloc[-1] / 1000),  # 轉為張
            "day_high": round(hist['High'].iloc[-1], 2),
            "day_low": round(hist['Low'].iloc[-1], 2),
            "week52_high": info.get('fiftyTwoWeekHigh'),
            "week52_low": info.get('fiftyTwoWeekLow'),
            "market_cap": info.get('marketCap'),
            "pe_ratio": info.get('trailingPE'),
            "pb_ratio": info.get('priceToBook'),
            "dividend_yield": info.get('dividendYield'),
        }
    except Exception as e:
        print(f"Error getting info for {symbol}: {e}")
        return None


@app.route('/')
def index():
    """首頁"""
    return render_template('index.html', popular_stocks=POPULAR_STOCKS)


@app.route('/api/quote/<code>')
def get_quote(code: str):
    """取得即時報價 API"""
    symbol = get_stock_symbol(code)
    info = get_stock_info(symbol)
    
    if info is None:
        return jsonify({"error": "無法取得股票資料，請確認股票代號"}), 404
    
    return jsonify(info)


@app.route('/api/chart/<code>')
def get_chart_data(code: str):
    """取得圖表資料 API"""
    period = request.args.get('period', '1y')
    
    # 對應期間參數
    period_map = {
        '1m': '1mo',
        '3m': '3mo',
        '6m': '6mo',
        '1y': '1y',
        '2y': '2y',
        '5y': '5y',
        'max': 'max',
    }
    yf_period = period_map.get(period, '1y')
    
    symbol = get_stock_symbol(code)
    df = fetch_stock_data(symbol, yf_period)
    
    if df.empty:
        return jsonify({"error": "無法取得歷史資料"}), 404
    
    indicators = calculate_technical_indicators(df)
    
    if not indicators:
        return jsonify({"error": "資料不足，無法計算技術指標"}), 400
    
    return jsonify(indicators)


@app.route('/api/popular')
def get_popular_stocks():
    """取得熱門股票列表"""
    return jsonify(POPULAR_STOCKS)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
