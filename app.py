from flask import Flask, render_template, request
import yfinance as yf

app = Flask(__name__)

def get_usd_inr_rate():
    """Fetch the latest USD/INR rate using yfinance."""
    try:
        fx = yf.Ticker("USDINR=X")
        hist = fx.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
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
                try:
                    ticker = yf.Ticker(sym)
                    info = ticker.info

               
                    if not info or ("longName" not in info and "shortName" not in info):
                        errors.append(f"Data not found for symbol: {sym}")
                        continue

                    price = info.get("currentPrice")
                    prev_close = info.get("previousClose")
                    open_price = info.get("open")
                    day_high = info.get("dayHigh")
                    day_low = info.get("dayLow")
                    market_cap = info.get("marketCap")
                    currency = info.get("currency", "USD")

         
                    change = None
                    change_percent = None
                    if price is not None and prev_close not in (None, 0):
                        change = price - prev_close
                        change_percent = (change / prev_close) * 100

                 
                    conversion_rate = None 

                    if currency == "INR":
                        conversion_rate = 1.0
                    elif currency == "USD":
                        if usd_inr_rate is None:
                            usd_inr_rate = get_usd_inr_rate()
                        conversion_rate = usd_inr_rate
                    else:
                     
                        conversion_rate = None

                    def to_inr(value):
                        if value is None or conversion_rate is None:
                            return None
                        return value * conversion_rate

                    price_inr = to_inr(price)
                    prev_close_inr = to_inr(prev_close)
                    open_inr = to_inr(open_price)
                    day_high_inr = to_inr(day_high)
                    day_low_inr = to_inr(day_low)
                    market_cap_inr = to_inr(market_cap)
                    change_inr = to_inr(change)

                    stock = {
                        "name": info.get("longName") or info.get("shortName") or "N/A",
                        "symbol": info.get("symbol", sym),
                        "currency": currency,
                        "price": price,
                        "price_inr": price_inr,
                        "marketCap": market_cap,
                        "marketCap_inr": market_cap_inr,
                        "previousClose": prev_close,
                        "previousClose_inr": prev_close_inr,
                        "open": open_price,
                        "open_inr": open_inr,
                        "dayHigh": day_high,
                        "dayHigh_inr": day_high_inr,
                        "dayLow": day_low,
                        "dayLow_inr": day_low_inr,
                        "change": change,
                        "change_inr": change_inr,
                        "changePercent": change_percent,
                        "conversionRate": conversion_rate,
                    }
                    stocks.append(stock)

                except Exception as e:
                    errors.append(f"Error fetching {sym}: {str(e)}")

            if stocks:
                primary_stock = stocks[0]

    return render_template(
        "index.html",
        stocks=stocks,
        primary_stock=primary_stock,
        errors=errors,
    )

if __name__ == "__main__":
    app.run(debug=True)
