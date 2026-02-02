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

# 台股資料庫（用於搜尋）
STOCK_DATABASE = {
    # 權值股
    "2330": "台積電", "2317": "鴻海", "2454": "聯發科", "2308": "台達電",
    "2382": "廣達", "2303": "聯電", "2412": "中華電", "2002": "中鋼",
    "1301": "台塑", "1303": "南亞", "1326": "台化", "2886": "兆豐金",
    "2881": "富邦金", "2882": "國泰金", "2884": "玉山金", "2885": "元大金",
    "2891": "中信金", "2892": "第一金", "2880": "華南金", "2883": "開發金",
    "2887": "台新金", "2890": "永豐金", "5880": "合庫金", "5876": "上海商銀",
    # 電子股
    "2409": "友達", "2408": "南亞科", "2301": "光寶科", "2912": "統一超",
    "2357": "華碩", "2353": "宏碁", "2324": "仁寶", "2356": "英業達",
    "2327": "國巨", "2379": "瑞昱", "2474": "可成", "3008": "大立光",
    "3711": "日月光投控", "2395": "研華", "2377": "微星", "6415": "矽力-KY",
    "3034": "聯詠", "2344": "華邦電", "3231": "緯創", "4904": "遠傳",
    "3045": "台灣大", "2345": "智邦", "3017": "奇鋐", "6669": "緯穎",
    "2603": "長榮", "2615": "萬海", "2609": "陽明", "2618": "長榮航",
    "2610": "華航", "1216": "統一", "2207": "和泰車", "2201": "裕隆",
    "9910": "豐泰", "1402": "遠東新", "1101": "台泥", "1102": "亞泥",
    "2823": "中壽", "2915": "潤泰全", "9904": "寶成", "2801": "彰銀",
    "2834": "臺企銀", "2812": "台中銀", "2836": "高雄銀", "2838": "聯邦銀",
    "5871": "中租-KY", "2105": "正新", "1210": "大成", "1227": "佳格",
    "2727": "王品", "2723": "美食-KY", "2049": "上銀", "1504": "東元",
    "2354": "鴻準", "6239": "力成", "2449": "京元電子", "3037": "欣興",
    "2006": "東和鋼鐵", "1605": "華新", "2014": "中鴻", "2015": "豐興",
    "2204": "中華", "9941": "裕融", "5269": "祥碩", "3661": "世芯-KY",
    "6770": "力積電", "3529": "力旺", "6005": "群益證", "6116": "彩晶",
    "2401": "凌陽", "3044": "健鼎", "3023": "信邦", "6176": "瑞儀",
    # ETF
    "0050": "元大台灣50", "0051": "元大中型100", "0052": "富邦科技",
    "0053": "元大電子", "0055": "元大MSCI金融", "0056": "元大高股息",
    "0057": "富邦摩台", "006205": "富邦上證", "006206": "元大上證50",
    "006208": "富邦台50", "00631L": "元大台灣50正2", "00632R": "元大台灣50反1",
    "00633L": "富邦上證正2", "00634R": "富邦上證反1", "00635U": "元大S&P黃金",
    "00636": "國泰中國A50", "00637L": "元大滬深300正2", "00638R": "元大滬深300反1",
    "00639": "富邦深100", "00642U": "元大S&P石油", "00645": "富邦日本",
    "00646": "元大S&P500", "00647L": "元大S&P500正2", "00648R": "元大S&P500反1",
    "00650L": "復華香港正2", "00651R": "復華香港反1", "00652": "富邦印度",
    "00655L": "國泰中國A50正2", "00656R": "國泰中國A50反1", "00657": "國泰日經225",
    "00660": "元大歐洲50", "00661": "元大日經225", "00662": "富邦NASDAQ",
    "00663L": "國泰臺灣加權正2", "00664R": "國泰臺灣加權反1", "00668": "國泰美國道瓊",
    "00669R": "國泰美國道瓊反1", "00670L": "富邦NASDAQ正2", "00671R": "富邦NASDAQ反1",
    "00675L": "富邦臺灣加權正2", "00676R": "富邦臺灣加權反1", "00677U": "富邦VIX",
    "00678": "群益NBI生技", "00679B": "元大美債20年", "00680L": "元大美債20正2",
    "00681R": "元大美債20反1", "00682U": "元大美元指數", "00683L": "元大美元指正2",
    "00684R": "元大美元指反1", "00685L": "群益臺灣加權正2", "00686R": "群益臺灣加權反1",
    "00688L": "國泰20年美債正2", "00689R": "國泰20年美債反1", "00690": "兆豐藍籌30",
    "00692": "富邦公司治理", "00693U": "街口道瓊銅", "00696B": "富邦美債7-10",
    "00700": "富邦恒生國企", "00701": "國泰股利精選30", "00703": "台新MSCI中國",
    "00706L": "元大S&P黃金正2", "00707R": "元大S&P黃金反1", "00708L": "元大S&P原油正2",
    "00709": "富邦歐洲", "00710B": "復華彭博高收益債", "00711B": "復華FH富時高息低波",
    "00712": "復華富時不動產", "00713": "元大台灣高息低波", "00714": "群益道瓊美國地產",
    "00715L": "街口投信布蘭特油正2", "00717": "富邦美國特別股", "00720B": "元大投資級公司債",
    "00728": "第一金工業30", "00730": "富邦臺灣優質高息", "00731": "復華富時高息低波",
    "00733": "富邦臺灣中小", "00735": "國泰臺韓科技", "00736": "國泰新興市場",
    "00737": "國泰AI+Robo", "00738U": "元大道瓊白銀", "00739": "元大MSCI A股",
    "00742": "新光內需收益", "00752": "中信中國高股息", "00753L": "中信中國50正2",
    "00757": "統一FANG+", "00762": "元大全球AI", "00763U": "街口布蘭特正2",
    "00770": "國泰北美科技", "00771": "元大US高息特別股", "00772B": "中信高評級公司債",
    "00773B": "中信優先金融債", "00774B": "新光US政府債1-3", "00775B": "新光投等債15+",
    "00830": "國泰費城半導體", "00850": "元大臺灣ESG永續",
    "00851": "台新全球AI", "00852L": "國泰美國費半正2", "00853U": "國泰美國費半反1",
    "00861": "元大全球未來關鍵科技", "00865B": "國泰US短期公債",
    "00875": "國泰網路資安", "00876": "元大全球5G", "00878": "國泰永續高股息",
    "00881": "國泰台灣5G+", "00882": "中信中國電動車", "00885": "富邦越南",
    "00886": "永豐台灣ESG", "00887": "永豐中國科技50", "00888": "永豐台灣智能車供應鏈",
    "00891": "中信關鍵半導體", "00892": "富邦台灣半導體", "00893": "國泰智能電動車",
    "00894": "中信小資高價30", "00895": "富邦未來車", "00896": "中信綠能及電動車",
    "00897": "富邦基因免疫生技", "00898": "國泰基因免疫革命", "00899": "FT潔淨能源",
    "00900": "富邦特選高股息30", "00901": "永豐智能車供應鏈", "00902": "中信電池及儲能",
    "00903": "富邦入息REITs+", "00904": "新光臺灣半導體30", "00905": "FT台灣Smart",
    "00907": "永豐優息存股", "00908": "富邦入息公司債", "00909": "國泰數位支付服務",
    "00910": "第一金太空衛星", "00911": "兆豐龍頭等權重", "00912": "中信臺灣智慧50",
    "00913": "兆豐台灣晶圓製造", "00915": "凱基優選高股息30", "00916": "國泰全球品牌50",
    "00917": "FT臺灣Smart", "00918": "大華優利高填息30", "00919": "群益台灣精選高息",
    "00920": "富邦全球電子競技", "00921": "兆豐龍頭等權重", "00922": "國泰台灣領袖50",
    "00923": "群益台ESG低碳50", "00924B": "國泰投資級A公司債", "00925B": "FT美國政府債0-1",
    "00926B": "凱基AAA至A公司債", "00927L": "群益半導體收益", "00928": "中信上游半導體",
    "00929": "復華台灣科技優息", "00930": "永豐ESG低碳高息", "00931": "統一台灣高息動能",
    "00932": "兆豐永續高息等權", "00933B": "國泰10Y+AAA至AA金融債", "00934B": "中信10Y+金融債",
    "00935": "野村臺灣新科技50", "00936": "台新臺灣永續高息中小", "00937B": "群益ESG投等債20+",
    "00939": "統一台灣高息動能", "00940": "元大台灣價值高息", "00941B": "中信美國公債20年",
    "00943B": "兆豐美國金融債", "00944": "野村趨勢動能高息", "00945B": "凱基美國非投等債",
    "00946B": "群益A級公司債", "00947B": "中信優息投資級債", "00948B": "中信彭博10年期美債",
    "00952B": "國泰A級公司債", "00953B": "國泰優選1-5Y非投等債",
}

# 建立反向索引（名稱 -> 代號）
STOCK_NAME_INDEX = {v: k for k, v in STOCK_DATABASE.items()}


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


@app.route('/api/search')
def search_stocks():
    """搜尋股票 (支援代號或名稱關鍵字)"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    results = []
    query_lower = query.lower()
    
    for code, name in STOCK_DATABASE.items():
        # 比對代號或名稱
        if query in code or query_lower in name.lower():
            results.append({
                "code": code,
                "name": name,
            })
        
        # 限制結果數量
        if len(results) >= 20:
            break
    
    # 優先顯示完全匹配的
    results.sort(key=lambda x: (
        0 if x['code'] == query else 1,
        0 if query_lower == x['name'].lower() else 1,
        len(x['code'])
    ))
    
    return jsonify(results[:20])


@app.route('/api/stock/<code>')
def get_stock_basic(code: str):
    """取得單一股票基本資訊（名稱）"""
    # 先查本地資料庫
    if code in STOCK_DATABASE:
        return jsonify({
            "code": code,
            "name": STOCK_DATABASE[code],
        })
    
    # 查不到就用 yfinance
    symbol = get_stock_symbol(code)
    info = get_stock_info(symbol)
    if info:
        return jsonify({
            "code": code,
            "name": info.get('name', code),
        })
    
    return jsonify({"error": "查無此股票"}), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
