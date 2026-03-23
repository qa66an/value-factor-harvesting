# value-factor-harvesting

Implementation of the classic Price-to-Book (P/B) value factor on a fully investable US equity universe using point-in-time data. Part of a systematic factor harvesting pipeline built on Sharadar data.

---

## Overview

This repo demonstrates end-to-end implementation of a classic value factor — from raw price and fundamental data through signal construction, universe filtering, decile ranking, and performance evaluation. The focus is on **correct implementation**: point-in-time data, no lookahead bias, proper universe construction, and statistical validation.

---

## Methodology

### Signal: Price-to-Book Ratio

```
P/B ratio = Price (t-1) / (Equity / Shares)
```

All fundamentals and prices pulled as of `before_date` — fully point-in-time, no lookahead bias.

### Date Construction

```
before_date:  last trading day before buy date  ← signal & fundamentals
buy_date:     first trading day of month        ← entry
sell_date:    last trading day of month         ← exit
Rebalance:    Monthly
```

### Universe

- Domestic common stock only
- Inflation-adjusted market cap filter: $200M base (year 2000) at 3% annually
- Removes negative, zero, and inf P/B ratios
- Winsorized at 99th percentile

$$\text{Limit}_{\text{min}} = \$200,000,000 \times (1.03)^{(\text{year} - 2000)}$$

### Portfolio Construction

- **Long**: top decile by P/B (lowest = cheapest), equal weighted
- **Short**: bottom decile by P/B (highest = most expensive), equal weighted
- **Long-short**: long minus short each month

### Data

- **Prices**: Sharadar SEP — point-in-time, no survivorship bias
- **Fundamentals**: Sharadar SF1 `ARQ` dimension — as-reported quarterly, `datekey` used for point-in-time filtering
- **Calendar**: NYSE via `pandas_market_calendars`

---

## Results

### Overall Performance (2000–2025)

| Strategy                   | Annual Return | Sharpe | T-Stat | P-Value | Win Rate | Max Drawdown |
| -------------------------- | ------------- | ------ | ------ | ------- | -------- | ------------ |
| Long only (top decile)     | 9.7%          | 0.32   | 1.64   | 0.103   | 53.8%    | -75.2%       |
| Short only (bottom decile) | -6.7%         | -0.29  | -1.48  | 0.141   | 41.7%    | -94.9%       |
| Long-Short (factor)        | 2.4%          | 0.11   | 0.56   | 0.573   | 46.2%    | -70.4%       |
| SPY (benchmark)            | 9.6%          | ~0.45  | —      | —       | —        | -51.0%       |

### Year-by-Year Long-Short Returns

| Year | Annual Return | Sharpe | Win Rate |
| ---- | ------------- | ------ | -------- |
| 2000 | +29.1%        | 0.40   | 58.3%    |
| 2001 | +46.2%        | 2.19   | 83.3%    |
| 2002 | +7.6%         | 0.37   | 50.0%    |
| 2003 | +18.3%        | 1.41   | 50.0%    |
| 2004 | +15.4%        | 2.49   | 75.0%    |
| 2005 | -0.7%         | -0.14  | 41.7%    |
| 2006 | +10.1%        | 1.22   | 58.3%    |
| 2007 | -32.2%        | -3.72  | 16.7%    |
| 2008 | -0.4%         | -0.01  | 41.7%    |
| 2009 | +41.2%        | 0.99   | 66.7%    |
| 2010 | +5.3%         | 0.55   | 50.0%    |
| 2011 | -6.0%         | -0.58  | 25.0%    |
| 2012 | +9.8%         | 1.32   | 58.3%    |
| 2013 | -3.3%         | -0.43  | 33.3%    |
| 2014 | -11.3%        | -0.80  | 33.3%    |
| 2015 | -21.0%        | -1.39  | 25.0%    |
| 2016 | +39.5%        | 2.66   | 75.0%    |
| 2017 | -20.1%        | -2.67  | 16.7%    |
| 2018 | -15.7%        | -1.23  | 41.7%    |
| 2019 | -17.1%        | -0.94  | 25.0%    |
| 2020 | -20.7%        | -0.64  | 33.3%    |
| 2021 | +28.3%        | 1.05   | 58.3%    |
| 2022 | +23.7%        | 1.27   | 58.3%    |
| 2023 | -0.2%         | -0.01  | 50.0%    |
| 2024 | -14.3%        | -0.91  | 33.3%    |
| 2025 | -0.3%         | -0.01  | 41.7%    |

---

## Discussion

### Statistical significance

```
Long-Short T-Stat:  0.56  → not statistically significant
Long-Short P-Value: 0.57  → cannot reject null hypothesis
Long only T-Stat:   1.64  → borderline, not significant at 95%
```

P/B does not produce a statistically significant premium on this universe and period. This is consistent with the academic literature — P/B has weakened as a standalone value signal on modern US equities due to the growing role of intangibles and share buybacks in driving firm value, neither of which are captured by book equity.

### Methodology validation

The same pipeline was used to test multiple signals across identical universe construction and evaluation code. The variation in results across signals confirms the infrastructure is clean — a pipeline with lookahead bias would inflate returns regardless of signal quality.

---

## References

- Fama, E. & French, K. (1992). _The Cross-Section of Expected Stock Returns_. Journal of Finance.
- Fama, E. & French, K. (2015). _A Five-Factor Asset Pricing Model_. Journal of Financial Economics.
- Arnott, R., Harvey, C., Kalesnik, V., Linnainmaa, J. (2021). _Reports of Value's Death May Be Greatly Exaggerated_. Financial Analysts Journal.

---

## Repository Structure

```
value-factor-harvesting/
├── functions.py               # Core pipeline functions
├── prepare_yearly_data.py     # Generates raw yearly CSVs from Sharadar
├── create_deciles.py          # Top/bottom decile construction
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
- `SHARADAR/SF1` — point-in-time fundamental data
