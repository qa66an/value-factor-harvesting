# value-factor-harvesting

Implementation of the classic Price-to-Sales (P/S) value factor on a fully investable US equity universe using point-in-time data. Built to document that the value premium is real, reproducible, and harvestable via a long-short construction — consistent with O'Shaughnessy (2011).

---

## Finding

On an investable mid/large cap universe (2000–2025), the P/S value factor delivers:

- **14.4% annualized return** on the long-short portfolio
- **Sharpe of 0.55** — stronger risk-adjusted return than SPY (~0.45)
- **58% win rate** on the long-short factor
- **−50.3% max drawdown** vs SPY's −51%

The long-short construction works because the short leg (expensive stocks) contributes meaningfully without the violent reversals seen in momentum shorts — consistent with the known asymmetry between value and momentum short legs.

---

## Methodology

### Signal: Price-to-Sales Ratio

Value is defined as low P/S — cheapest stocks relative to revenue:

```
P/S ratio = Price (t-1) / (Revenue / Shares)
```

All fundamentals and prices pulled as of `before_date` (trading day before buy date) — fully point-in-time, no lookahead bias.

### Date Construction

```
before_date:    last trading day before buy date  ← signal & fundamentals
buy_date:       first trading day of month        ← entry
sell_date:      last trading day of month         ← exit (1 month hold)
Rebalance:      Monthly
```

### Universe

- Domestic common stock only (primary, secondary, and standard class)
- Inflation-adjusted market cap filter: $200M base (year 2000), adjusted at 3% annually
- Removes negative, zero, and inf P/S ratios (distressed/zero-revenue stocks)
- Winsorized at 99th percentile to remove extreme outliers

$$\text{Limit}_{\text{min}} = \$200,000,000 \times (1.03)^{(\text{year} - 2000)}$$

### Portfolio Construction

- **Long leg**: top decile by P/S (lowest ratio = cheapest = value), equal weighted
- **Short leg**: bottom decile by P/S (highest ratio = most expensive), equal weighted
- **Long-short**: long return minus short return each month

### Data

- **Price data**: Sharadar SEP — point-in-time prices, no survivorship bias
- **Fundamentals**: Sharadar SF1 — point-in-time revenue, equity, net income, shares
- **Trading calendar**: NYSE calendar via `pandas_market_calendars`

---

## Results

### Overall Performance (2000–2025)

| Strategy                   | Annual Return | Sharpe | T-Stat | P-Value | Win Rate | Max Drawdown |
| -------------------------- | ------------- | ------ | ------ | ------- | -------- | ------------ |
| Long only (top decile)     | 14.3%         | 0.49   | 2.50   | 0.013   | 56.1%    | -66.3%       |
| Short only (bottom decile) | 0.1%          | 0.00   | 0.01   | 0.991   | 46.8%    | -86.6%       |
| Long-Short (factor)        | 14.4%         | 0.55   | 2.82   | 0.005   | 58.0%    | -50.3%       |
| SPY (benchmark)            | 9.6%          | ~0.45  | —      | —       | —        | -51.0%       |

### Year-by-Year Long-Short Returns

| Year | Annual Return | Sharpe | Win Rate |
| ---- | ------------- | ------ | -------- |
| 2000 | +63.8%        | 0.64   | 66.7%    |
| 2001 | +45.9%        | 0.97   | 58.3%    |
| 2002 | +43.6%        | 1.39   | 66.7%    |
| 2003 | +7.7%         | 0.65   | 58.3%    |
| 2004 | +19.2%        | 1.60   | 58.3%    |
| 2005 | +7.1%         | 0.97   | 58.3%    |
| 2006 | +20.7%        | 2.82   | 75.0%    |
| 2007 | -16.4%        | -1.70  | 33.3%    |
| 2008 | -9.2%         | -0.41  | 33.3%    |
| 2009 | +82.9%        | 2.07   | 75.0%    |
| 2010 | +8.1%         | 0.76   | 75.0%    |
| 2011 | +5.6%         | 0.44   | 58.3%    |
| 2012 | +14.5%        | 1.53   | 66.7%    |
| 2013 | +21.2%        | 2.02   | 75.0%    |
| 2014 | -0.9%         | -0.06  | 50.0%    |
| 2015 | -6.4%         | -0.45  | 41.7%    |
| 2016 | +42.7%        | 2.37   | 75.0%    |
| 2017 | -6.3%         | -0.53  | 33.3%    |
| 2018 | -14.7%        | -1.35  | 33.3%    |
| 2019 | -5.9%         | -0.25  | 50.0%    |
| 2020 | -14.0%        | -0.50  | 50.0%    |
| 2021 | +75.8%        | 2.37   | 75.0%    |
| 2022 | +57.9%        | 1.69   | 66.7%    |
| 2023 | +14.1%        | 0.90   | 66.7%    |
| 2024 | -4.3%         | -0.28  | 41.7%    |
| 2025 | -5.0%         | -0.24  | 66.7%    |

---

## Discussion

### Statistical significance

```
Long-Short T-Stat:  2.82  → significant at 99% confidence
Long-Short P-Value: 0.005 → 0.5% probability this is luck
Long only T-Stat:   2.50  → significant at 95% confidence
Short only T-Stat:  0.01  → not significant (as expected)
```

The L/S factor return is statistically significant at the 99% confidence level — the premium is not a product of random chance. The short leg correctly shows no significance on its own, confirming alpha comes from the spread, not either leg in isolation.

### Why P/S over P/E or P/B

P/S is O'Shaughnessy's best single value metric and the cleanest signal on this universe:

```
P/E  →  meaningless when earnings are negative
P/B  →  distorted by share buybacks and intangibles (tech stocks)
P/S  →  always interpretable, harder to manipulate, works across sectors
```

### Why the L/S works better than momentum L/S

The value short leg (expensive stocks) behaves very differently from the momentum short leg (recent losers):

```
Momentum shorts → mean-revert violently after market selloffs (2009 crash)
Value shorts    → expensive stocks drift or revert slowly → less dangerous
```

This produces a short leg that adds diversification without the crash risk inherent in momentum shorts. The result is a cleaner L/S with lower max drawdown (−50%) than either the long leg alone (−66%) or SPY (−51%).

### Known weakness: growth periods

Value underperforms in prolonged growth/tech rallies — 2017–2020 shows four consecutive years of negative or near-zero L/S returns. This is the well-documented value drawdown period consistent with Arnott et al. (2021). The factor recovered sharply in 2021–2022 with the rate hiking cycle, consistent with value's historical behavior in rising rate environments.

### Comparison with O'Shaughnessy

O'Shaughnessy documents P/S as his strongest single value factor on an all-stocks universe, delivering ~15% annualized vs ~13% for the all-stocks benchmark (+15% spread). This implementation delivers 14.4% on an investable universe vs SPY's 9.6% (+50% spread), confirming the factor is robust to universe constraints and time period.

---

## References

- O'Shaughnessy, J. (2011). _What Works on Wall Street_. McGraw-Hill.
- Fama, E. & French, K. (1992). _The Cross-Section of Expected Stock Returns_. Journal of Finance.
- Arnott, R., Harvey, C., Kalesnik, V., Linnainmaa, J. (2021). _Reports of Value's Death May Be Greatly Exaggerated_. Financial Analysts Journal.
- Israel, R. & Moskowitz, T. (2013). _The Role of Shorting, Firm Size, and Time on Market Anomalies_. Journal of Financial Economics.

---

## Repository Structure

```
value-factor-harvesting/
├── functions.py               # Core pipeline functions
├── prepare_yearly_data.py     # Generates raw yearly CSVs from Sharadar
├── create_deciles.py          # Top/bottom decile construction by P/S ratio
├── eval.py                    # Performance stats and results
├── requirements.txt
└── README.md
```

---

## Requirements

```
duckdb
pandas
numpy
scipy
pandas_market_calendars
python-dateutil
```

---

## Data

Requires a Sharadar subscription via Nasdaq Data Link:

- `SHARADAR/SEP` — daily equity prices
- `SHARADAR/SF1` — point-in-time fundamental data (revenue, equity, net income, shares)
