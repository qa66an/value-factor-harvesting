import glob
import pandas as pd
from functions import get_stats
import numpy as np

# ── Load top decile (long leg) ────────────────────────────────────────────────
top_files = glob.glob("./years_top_deciles/*.csv")
df_top = pd.concat([pd.read_csv(f) for f in top_files], ignore_index=True)
df_top["buy_date"] = pd.to_datetime(df_top["buy_date"])

# ── Load bottom decile (short leg) ───────────────────────────────────────────
bot_files = glob.glob("./years_bottom_deciles/*.csv")
df_bot = pd.concat([pd.read_csv(f) for f in bot_files], ignore_index=True)
df_bot["buy_date"] = pd.to_datetime(df_bot["buy_date"])

# ── Equal-weight each leg per month ──────────────────────────────────────────
long_ret = df_top.groupby("buy_date")["pl_pct"].mean().rename("long")
short_ret = df_bot.groupby("buy_date")["pl_pct"].mean().rename("short")

# ── Combine: long-short return = long - short (you profit when bottom loses) ─
monthly = pd.concat([long_ret, short_ret], axis=1).dropna()
monthly["ls_return"] = monthly["long"] - monthly["short"]  # <-- the magic line


# ── Print all three legs side by side ────────────────────────────────────────
results = pd.DataFrame(
    [
        get_stats(monthly["long"], "Long only (top decile)"),
        get_stats(-monthly["short"], "Short only (bottom decile)"),
        get_stats(monthly["ls_return"], "Long-Short (factor)"),
    ]
)

print(results.set_index("Strategy").T.to_string())

# ── Year-by-year for the L/S portfolio ───────────────────────────────────────
monthly["year"] = monthly.index.year
yearly = monthly.groupby("year")["ls_return"].agg(
    Annual_Return=lambda x: (1 + x.mean()) ** 12 - 1,
    Sharpe=lambda x: (x.mean() / x.std()) * np.sqrt(12),
    Win_Rate=lambda x: (x > 0).mean(),
)
print("\n===== Long-Short Year-by-Year =====")
print(yearly.round(4).to_string())

