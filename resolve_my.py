from stock_screener import resolve_ticker

my_top_30_names = ["MAYBANK", "TENAGA", "PBBANK", "CIMB", "PMETAL", "YTL", "YTLPOWR", "DIALOG", "IHH", "CELCOMDIGI", "TM", "MRDIY", "PETGAS", "SIME", "MISC", "KLK", "IOICORP", "PPB", "NESTLE", "MAXIS", "INARI", "GENTING", "GENM", "AMBANK", "RHBBANK", "HLBANK", "CARLSBG", "SUNWAY", "GAMUDA"]

resolved = []
for name in my_top_30_names:
    ticker, shortname = resolve_ticker(name, "Malaysia Stocks")
    resolved.append(ticker)

print(resolved)
