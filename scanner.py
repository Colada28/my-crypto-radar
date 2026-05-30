def scan_binance():
    try:
        markets = binance.load_markets()
    except Exception as e:
        print("Ошибка load_markets:", e)
        return

    symbols = [s for s in markets if s.endswith("/USDT")]

    for symbol in symbols:
        try:
            ohlcv = binance.fetch_ohlcv(symbol, timeframe="5m", limit=12)
        except:
            continue

        if len(ohlcv) < 2:
            continue

        closes = [c[4] for c in ohlcv]
        volumes = [c[5] for c in ohlcv]

        now_price = closes[-1]
        window_candles = max(1, WINDOW_MIN // 5)

        if len(closes) <= window_candles:
            continue

        past_price = closes[-1 - window_candles]
        window_volume = sum(volumes[-window_candles:])

        if past_price == 0:
            continue

        change_pct = (now_price - past_price) / past_price * 100

        if window_volume * now_price < MIN_VOLUME_USDT:
            continue

        if change_pct >= PUMP_THRESHOLD:
            send(
                f"PUMP\n"
                f"{symbol}\n"
                f"Изменение: {change_pct:.2f}% за {WINDOW_MIN} минут\n"
                f"Объём: {int(window_volume * now_price)} USDT"
            )

        elif change_pct <= DUMP_THRESHOLD:
            send(
                f"DUMP\n"
                f"{symbol}\n"
                f"Изменение: {change_pct:.2f}% за {WINDOW_MIN} минут\n"
                f"Объём: {int(window_volume * now_price)} USDT"
            )


def radar_loop():
    print("Radar loop started")
    send("Binance radar started")
    send("Test message: bot is working")
    while True:
        try:
            scan_binance()
        except Exception as e:
            print("Ошибка в radar_loop:", e)
        time.sleep(INTERVAL_SEC)
