from flask import Flask, render_template, request
import yfinance as yf
from binance.client import Client
import plotly.graph_objects as go

app = Flask(__name__)

binance = None
binance_disabled = False

def get_usd_inr_rate():
    try:
        fx = yf.Ticker("USDINR=X")
        hist = fx.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except:
        return None


def fetch_from_binance(symbol):
    global binance, binance_disabled
    if binance_disabled:
        return None

    try:
        if binance is None:
            binance = Client()

        symbol = symbol.upper()
        if not symbol.endswith(("USDT", "BUSD", "BTC")):
            symbol = symbol + "USDT"

        data = binance.get_ticker(symbol=symbol)
        price = float(data["lastPrice"])
        prev_price = float(data.get("prevClosePrice", 0))

        change = price - prev_price if prev_price else None
        change_percent = (change / prev_price * 100) if prev_price else None

        return {
            "name": symbol.replace("USDT", ""),
            "symbol": symbol,
            "currency": "USDT",
            "price": price,
            "marketCap": None,
            "previousClose": prev_price,
            "open": float(data.get("openPrice", 0)),
            "dayHigh": float(data.get("highPrice", 0)),
            "dayLow": float(data.get("lowPrice", 0)),
            "change": change,
            "changePercent": change_percent
        }

    except:
        binance_disabled = True
        return None



def generate_candles(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo", interval="1d")
        if hist.empty:
            return None

        fig = go.Figure(data=[go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close']
        )])

        fig.update_layout(
            xaxis_rangeslider_visible=False,
            template="plotly_dark",
            height=350,
            margin=dict(l=10, r=10, t=10, b=10)
        )

        return fig.to_html(full_html=False, config={"displayModeBar": False})
    except:
        return None


@app.route("/", methods=["GET", "POST"])
def index():
    stocks = []
    primary_stock = None
    errors = []
    usd_inr_rate = None

    if request.method == "POST":
        raw = request.form.get("company", "").strip()
        if raw:
            symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]

            for sym in symbols:
                stock_data = None

                if sym.endswith(("USDT", "BTC", "ETH", "BUSD")) or len(sym) <= 5:
                    stock_data = fetch_from_binance(sym)

                if stock_data is None:
                    try:
                        ticker = yf.Ticker(sym)
                        info = ticker.info
                    except:
                        info = None

                    if not info or ("longName" not in info and "shortName" not in info):
                        errors.append(f"No data found for {sym}")
                        continue

                    stock_data = {
                        "name": info.get("longName") or info.get("shortName") or sym,
                        "symbol": info.get("symbol", sym),
                        "currency": info.get("currency", "USD"),
                        "price": info.get("currentPrice"),
                        "marketCap": info.get("marketCap"),
                        "previousClose": info.get("previousClose"),
                        "open": info.get("open"),
                        "dayHigh": info.get("dayHigh"),
                        "dayLow": info.get("dayLow"),
                        "change": None,
                        "changePercent": None
                    }

                    if stock_data["price"] and stock_data["previousClose"]:
                        stock_data["change"] = stock_data["price"] - stock_data["previousClose"]
                        stock_data["changePercent"] = (stock_data["change"] / stock_data["previousClose"]) * 100

                currency = stock_data["currency"]
                conversion_rate = None

                if currency == "INR":
                    conversion_rate = 1.0
                elif currency in ["USD", "USDT", "BUSD"]:
                    if usd_inr_rate is None:
                        usd_inr_rate = get_usd_inr_rate()
                    conversion_rate = usd_inr_rate

                def to_inr(v):
                    return round(v * conversion_rate, 2) if v and conversion_rate else None

                stock_data.update({
                    "price_inr": to_inr(stock_data["price"]),
                    "previousClose_inr": to_inr(stock_data["previousClose"]),
                    "open_inr": to_inr(stock_data["open"]),
                    "dayHigh_inr": to_inr(stock_data["dayHigh"]),
                    "dayLow_inr": to_inr(stock_data["dayLow"]),
                    "marketCap_inr": to_inr(stock_data["marketCap"]),
                    "change_inr": to_inr(stock_data["change"]),
                    "conversionRate": conversion_rate,
                })

                stocks.append(stock_data)

    if stocks:
        primary_stock = stocks[0]

    chart = generate_candles(primary_stock["symbol"]) if primary_stock else None

    return render_template("index.html", stocks=stocks, primary_stock=primary_stock, errors=errors, chart=chart)


if __name__ == "__main__":
    app.run(debug=True)
