from datetime import datetime, timedelta
import duckdb
import pandas as pd
from dateutil.relativedelta import relativedelta
import pandas_market_calendars as mcal
import numpy as np
from scipy import stats


def create_sep_db(csv_path, db_path="./db_files/sep.duckdb"):

    con = duckdb.connect(db_path)

    # READ CSV INTO DB
    con.execute(
        f"""
    CREATE TABLE IF NOT EXISTS sep AS
    SELECT *
    FROM read_csv_auto('{csv_path}', IGNORE_ERRORS=true)
    """
    )

    # INDEX (for date-based queries + joins)
    con.execute("CREATE INDEX IF NOT EXISTS idx_sep_date_ticker ON sep(date, ticker);")

    # DESCRIBE TABLE
    print(
        con.execute(
            """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT ticker) AS unique_tickers
        FROM sep;
        """
        ).fetchdf()
    )


def add_beta_columns(spy_path, db_path="./db_files/sep.duckdb"):
    con = duckdb.connect(db_path)
    # ============================================================================
    # STEP 1: Load SPY data into DuckDB
    # ============================================================================
    print("Loading SPY data...")
    con.execute(
        f"""
    CREATE TABLE IF NOT EXISTS spy AS
    SELECT *
    FROM read_csv_auto('{spy_path}', IGNORE_ERRORS=true)
    """
    )

    con.execute("CREATE INDEX IF NOT EXISTS idx_spy_date ON spy(date);")

    # ============================================================================
    # STEP 2: Calculate returns for SPY
    # ============================================================================
    print("Calculating SPY returns...")
    con.execute(
        """
    CREATE OR REPLACE TABLE spy_returns AS
    SELECT 
        date,
        close,
        (close - LAG(close) OVER (ORDER BY date)) / LAG(close) OVER (ORDER BY date) AS spy_returns
    FROM spy
    ORDER BY date
    """
    )

    # ============================================================================
    # STEP 3: Calculate returns for SEP stocks
    # ============================================================================
    print("Calculating stock returns...")
    con.execute(
        """
    CREATE OR REPLACE TABLE sep_with_returns AS
    SELECT 
        ticker,
        date,
        close,
        (close - LAG(close) OVER (PARTITION BY ticker ORDER BY date)) / 
        LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS returns
    FROM sep
    ORDER BY ticker, date
    """
    )

    # ============================================================================
    # STEP 4: Join SEP with SPY returns
    # ============================================================================
    print("Joining stock and SPY returns...")
    con.execute(
        """
    CREATE OR REPLACE TABLE sep_joined AS
    SELECT 
        s.ticker,
        s.date,
        s.close,
        s.returns,
        spy.spy_returns
    FROM sep_with_returns s
    LEFT JOIN spy_returns spy ON s.date = spy.date
    ORDER BY s.ticker, s.date
    """
    )

    # ============================================================================
    # STEP 5: Calculate rolling beta, upside beta, and downside beta (126 days)
    # ============================================================================
    print("Calculating 126-day rolling beta, upside beta, and downside beta...")
    con.execute(
        """
    CREATE OR REPLACE TABLE sep_with_beta AS
    SELECT 
        ticker,
        date,
        close,
        returns,
        spy_returns,
        -- Standard beta (126 days)
        COVAR_POP(returns, spy_returns) OVER (
            PARTITION BY ticker 
            ORDER BY date 
            ROWS BETWEEN 126 PRECEDING AND 1 PRECEDING
        ) / NULLIF(
            VAR_POP(spy_returns) OVER (
                PARTITION BY ticker 
                ORDER BY date 
                ROWS BETWEEN 126 PRECEDING AND 1 PRECEDING
            ), 0
        ) AS beta_126,
        -- Upside beta (when SPY returns > 0)
        COVAR_POP(
            CASE WHEN spy_returns > 0 THEN returns ELSE NULL END,
            CASE WHEN spy_returns > 0 THEN spy_returns ELSE NULL END
        ) OVER (
            PARTITION BY ticker 
            ORDER BY date 
            ROWS BETWEEN 126 PRECEDING AND 1 PRECEDING
        ) / NULLIF(
            VAR_POP(
                CASE WHEN spy_returns > 0 THEN spy_returns ELSE NULL END
            ) OVER (
                PARTITION BY ticker 
                ORDER BY date 
                ROWS BETWEEN 126 PRECEDING AND 1 PRECEDING
            ), 0
        ) AS upside_beta_126,
        -- Downside beta (when SPY returns < 0)
        COVAR_POP(
            CASE WHEN spy_returns < 0 THEN returns ELSE NULL END,
            CASE WHEN spy_returns < 0 THEN spy_returns ELSE NULL END
        ) OVER (
            PARTITION BY ticker 
            ORDER BY date 
            ROWS BETWEEN 126 PRECEDING AND 1 PRECEDING
        ) / NULLIF(
            VAR_POP(
                CASE WHEN spy_returns < 0 THEN spy_returns ELSE NULL END
            ) OVER (
                PARTITION BY ticker 
                ORDER BY date 
                ROWS BETWEEN 126 PRECEDING AND 1 PRECEDING
            ), 0
        ) AS downside_beta_126
    FROM sep_joined
    ORDER BY ticker, date
    """
    )

    # ============================================================================
    # STEP 6: Update original SEP table with beta columns
    # ============================================================================
    print("Adding beta columns to original SEP table...")
    con.execute(
        """
    ALTER TABLE sep ADD COLUMN IF NOT EXISTS beta_126 DOUBLE;
    ALTER TABLE sep ADD COLUMN IF NOT EXISTS upside_beta_126 DOUBLE;
    ALTER TABLE sep ADD COLUMN IF NOT EXISTS downside_beta_126 DOUBLE;
    """
    )

    con.execute(
        """
    UPDATE sep
    SET 
        beta_126 = b.beta_126,
        upside_beta_126 = b.upside_beta_126,
        downside_beta_126 = b.downside_beta_126
    FROM sep_with_beta b
    WHERE sep.ticker = b.ticker AND sep.date = b.date
    """
    )

    # ============================================================================
    # STEP 7: Verify results
    # ============================================================================
    print("\nVerification:")
    print("Sample data with beta values:")
    result = con.execute(
        """
    SELECT 
        ticker,
        date,
        close,
        beta_126,
        upside_beta_126,
        downside_beta_126
    FROM sep
    WHERE beta_126 IS NOT NULL
    ORDER BY ticker, date DESC
    LIMIT 10
    """
    ).fetchdf()

    print(result)

    print("\nBeta statistics:")
    stats = con.execute(
        """
    SELECT 
        COUNT(*) AS total_rows,
        COUNT(beta_126) AS rows_with_beta_126,
        COUNT(upside_beta_126) AS rows_with_upside_beta,
        COUNT(downside_beta_126) AS rows_with_downside_beta,
        AVG(beta_126) AS avg_beta_126,
        AVG(upside_beta_126) AS avg_upside_beta_126,
        AVG(downside_beta_126) AS avg_downside_beta_126,
        MIN(beta_126) AS min_beta_126,
        MAX(beta_126) AS max_beta_126
    FROM sep
    """
    ).fetchdf()

    print(stats)

    # ============================================================================
    # CLEANUP: Drop temporary tables (optional)
    # ============================================================================
    print("\nCleaning up temporary tables...")
    con.execute("DROP TABLE IF EXISTS spy_returns")
    con.execute("DROP TABLE IF EXISTS sep_with_returns")
    con.execute("DROP TABLE IF EXISTS sep_joined")
    con.execute("DROP TABLE IF EXISTS sep_with_beta")

    print(
        "\n✅ Done! Beta columns (beta_126, upside_beta_126, downside_beta_126) added to SEP table."
    )

    con.close()


def create_sf1_db(csv_path, db_path="./db_files/sf1_core.duckdb"):
    con = duckdb.connect(db_path)
    con.execute("DROP TABLE IF EXISTS sf1_core")
    con.execute(
        f"""
    CREATE TABLE sf1_core AS
    SELECT
        ticker,
        datekey::DATE      AS calendardate,

        -- shares
        sharesbas::DOUBLE       AS sharesbas,
        shareswa::DOUBLE        AS shareswa,

        -- fundamentals
        equity::DOUBLE          AS equity,
        assets::DOUBLE          AS assets,
        netinccmn::DOUBLE       AS net_income,
        revenue::DOUBLE         AS revenue,
        
    FROM read_csv_auto('{csv_path}')

    WHERE
        dimension = 'ARQ'
        AND calendardate IS NOT NULL
    """
    )

    print(con.execute("DESCRIBE sf1_core").df())
    print("Rows:", con.execute("SELECT COUNT(*) FROM sf1_core").fetchone()[0])
    print(
        "Tickers:",
        con.execute("SELECT COUNT(DISTINCT ticker) FROM sf1_core").fetchone()[0],
    )

    con.close()


# ================================
# TRADING CALENDAR
# ================================
def load_trading_calendar(start_date="1990-01-01", end_date="2026-01-01"):
    nyse = mcal.get_calendar("NYSE")
    schedule = nyse.schedule(start_date, end_date)
    trading_days = pd.to_datetime(schedule.index)
    return trading_days.tolist()


def prev_trading_day(trading_days, target_date):
    for d in reversed(trading_days):
        if d <= target_date:
            return d
    return None


def next_trading_day(trading_days, target_date):
    for d in trading_days:
        if d >= target_date:
            return d
    return None


# ================================
# MOMENTUM WINDOW
# ================================
def momentum_window(buy_date_str, trading_days):
    buy_date = datetime.strptime(buy_date_str, "%Y-%m-%d")

    # skip most recent month
    end_month_date = buy_date - relativedelta(months=1)
    start_month_date = buy_date - relativedelta(months=13)

    momentum_end = prev_trading_day(trading_days, end_month_date)
    momentum_start = prev_trading_day(trading_days, start_month_date)

    return momentum_start.date(), momentum_end.date()


# ================================
# HOLDING WINDOW
# ================================
def holding_window_one_month(buy_date_str, trading_days):
    buy_date = datetime.strptime(buy_date_str, "%Y-%m-%d")

    entry_date = next_trading_day(trading_days, buy_date)

    # end of next month trick
    target_exit = entry_date.replace(day=28) + timedelta(days=4)
    target_exit = target_exit.replace(day=1) - timedelta(days=1)

    exit_date = prev_trading_day(trading_days, target_exit)

    return entry_date.date(), exit_date.date()


# ================================
# MAIN DATE PIPELINE
# ================================
def get_momentum_and_holding_dates(buy_date_str, trading_days):
    buy_date = datetime.strptime(buy_date_str, "%Y-%m-%d")

    # ensure enough buffer for lookback + holding
    start = (buy_date - relativedelta(months=8)).strftime("%Y-%m-%d")
    end = (buy_date + relativedelta(months=2)).strftime("%Y-%m-%d")

    mom_start, mom_end = momentum_window(buy_date_str, trading_days)
    buy_date, sell_date = holding_window_one_month(buy_date_str, trading_days)

    print("Momentum start :", mom_start)
    print("Momentum end   :", mom_end)
    print("Hold entry     :", buy_date)
    print("Hold exit      :", sell_date)

    return mom_start, mom_end, buy_date, sell_date


# ================================
# DUCKDB QUERY
# ================================
def get_four_date_prices(db_path, date1, date2, date3, date4):
    con = duckdb.connect(db_path)

    query = f"""
    SELECT
        ticker,

        '{date1}' AS momentum_start,
        '{date2}' AS momentum_end,
        '{date3}' AS buy_date,
        '{date4}' AS sell_date,

        MAX(CASE WHEN date = '{date1}' THEN closeadj END) AS start_price,
        MAX(CASE WHEN date = '{date2}' THEN closeadj END) AS end_price,
        MAX(CASE WHEN date = '{date3}' THEN close END) AS buy_price,
        MAX(CASE WHEN date = '{date2}' THEN beta_126 END) AS beta,
        MAX(CASE WHEN date = '{date4}' THEN close END) AS sell_price

    FROM sep
    WHERE date IN ('{date1}', '{date2}', '{date3}', '{date4}')
    GROUP BY ticker
    """

    df = con.execute(query).fetchdf()
    con.close()

    # metrics
    df["momentum_pct"] = (df["end_price"] - df["start_price"]) / df["start_price"]
    df.insert(df.columns.get_loc("buy_price"), "momentum_pct", df.pop("momentum_pct"))

    df["pl_pct"] = (df["sell_price"] - df["buy_price"]) / df["buy_price"]

    return df


# ================================
# GENERATE MONTHLY SIGNALS
# ================================
def generate_monthly_dates(start_year, end_year):
    nyse = mcal.get_calendar("NYSE")
    dates = {}
    for year in range(start_year, end_year):
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        # all trading days in the year
        trading_days = nyse.schedule(start_date=start, end_date=end).index
        trading_days = pd.to_datetime(trading_days)

        # first trading day of each month
        first_days = (
            trading_days.to_series()
            .groupby(trading_days.to_period("M"))
            .min()
            .dt.strftime("%Y-%m-%d")
            .tolist()
        )

        dates[str(year)] = first_days
    return dates


def get_fundementals_for_dates(df, sf1_db_path, meta_data_path):
    con = duckdb.connect()
    con.execute(f"ATTACH '{sf1_db_path}' AS sf1db")
    con.register("prices", df)
    result = con.execute(
        """
        SELECT
            p.*,

            (
                SELECT s.sharesbas
                FROM sf1db.sf1_core s
                WHERE s.ticker = p.ticker
                  AND s.calendardate <= CAST(p.before_date AS DATE)
                ORDER BY s.calendardate DESC
                LIMIT 1
            ) AS sharesbas,

            (
                SELECT s.shareswa
                FROM sf1db.sf1_core s
                WHERE s.ticker = p.ticker
                  AND s.calendardate <= CAST(p.before_date AS DATE)
                ORDER BY s.calendardate DESC
                LIMIT 1
            ) AS shareswa,

            (
                SELECT s.equity
                FROM sf1db.sf1_core s
                WHERE s.ticker = p.ticker
                  AND s.calendardate <= CAST(p.before_date AS DATE)
                ORDER BY s.calendardate DESC
                LIMIT 1
            ) AS equity,

            (
                SELECT s.net_income
                FROM sf1db.sf1_core s
                WHERE s.ticker = p.ticker
                  AND s.calendardate <= CAST(p.before_date AS DATE)
                ORDER BY s.calendardate DESC
                LIMIT 1
            ) AS net_income,

            (
                SELECT s.assets
                FROM sf1db.sf1_core s
                WHERE s.ticker = p.ticker
                  AND s.calendardate <= CAST(p.before_date AS DATE)
                ORDER BY s.calendardate DESC
                LIMIT 1
            ) AS assets,
            
            (
                SELECT s.revenue
                FROM sf1db.sf1_core s
                WHERE s.ticker = p.ticker
                AND s.calendardate <= CAST(p.before_date AS DATE)
                ORDER BY s.calendardate DESC
                LIMIT 1
            ) AS revenue

        FROM prices p
        """
    ).df()
    result["pb_ratio"] = result["before_price"] / (
        result["equity"] / result["sharesbas"]
    )
    result["pe_ratio"] = result["before_price"] / (
        result["net_income"] / result["sharesbas"]
    )
    result["mc_before_date"] = result["sharesbas"] * result["before_price"]
    meta = pd.read_csv(f"{meta_data_path}", usecols=["ticker", "category"])
    meta.drop_duplicates(subset=["ticker"], inplace=True)
    lookup = meta.set_index("ticker")["category"]
    result["category"] = result["ticker"].map(lookup)
    return result


def create_top_and_bottom_deciles(file, top_decile_path, bottom_decile_path):
    df = pd.read_csv(file)
    year = int(df["buy_date"].iloc[0][:4])
    df = df[
        (df["category"] == "Domestic Common Stock")
        | (df["category"] == "Domestic Common Stock Primary Class")
        | (df["category"] == "Domestic Common Stock Secondary Class")
    ]
    limit_min = 200_000_000 * (1.03 ** (year - 2000))
    df = df[(df["mc_before_date"] > limit_min)]
    df = df[df["pb_ratio"] > 0]
    df = df.dropna(subset=["pb_ratio"])
    df = df[~np.isinf(df["pb_ratio"])]
    df = df[df["pb_ratio"] < df["pb_ratio"].quantile(0.99)]

    df = df.sort_values(by=["buy_date", "pb_ratio"], ascending=[True, True])
    df_top_decile = df.groupby("buy_date", group_keys=False).apply(
        lambda x: x.head(len(x) // 10)
    )
    df_bottom_decile = df.groupby("buy_date", group_keys=False).apply(
        lambda x: x.tail(len(x) // 10)
    )
    df_top_decile.to_csv(f"./{top_decile_path}/top_decile_{year}.csv", index=False)
    df_bottom_decile.to_csv(
        f"./{bottom_decile_path}/bottom_decile_{year}.csv", index=False
    )
    print(f"Processed year {year}: top and bottom deciles saved.")


def get_stats(r, label):
    cum = (1 + r).cumprod()
    t_stat, p_value = stats.ttest_1samp(r.dropna(), 0)
    return {
        "Strategy": label,
        "Avg Monthly Return": r.mean(),
        "Annualized Return": (1 + r.mean()) ** 12 - 1,
        "Annualized Vol": r.std() * np.sqrt(12),
        "Sharpe Ratio": (r.mean() / r.std()) * np.sqrt(12),
        "T-Stat": t_stat,
        "P-Value": p_value,
        "Win Rate": (r > 0).mean(),
        "Best Month": r.max(),
        "Worst Month": r.min(),
        "Max Drawdown": (cum / cum.cummax() - 1).min(),
    }


def get_three_date_prices(db_path, date1, date2, date3):
    """
    Returns one row per ticker with prices on three specific dates.
    """

    con = duckdb.connect(db_path)

    query = f"""
    SELECT
        ticker,

        '{date1}' AS before_date,
        '{date2}' AS buy_date,
        '{date3}' AS sell_date,

        MAX(CASE WHEN date = '{date1}' THEN close END) AS before_price,
        MAX(CASE WHEN date = '{date2}' THEN close END) AS buy_price,
        MAX(CASE WHEN date = '{date3}' THEN close END) AS sell_price

    FROM sep
    WHERE date IN ('{date1}', '{date2}', '{date3}')
    GROUP BY ticker
    """

    df = con.execute(query).fetchdf()
    con.close()
    df["pl_pct"] = (df["sell_price"] - df["buy_price"]) / df["buy_price"]

    return df


def prev_trading_day_before(trading_days, target_date):
    for d in reversed(trading_days):
        if d < target_date:
            return d
    return None


def get_value_dates(buy_date_str, trading_days):
    buy_date = datetime.strptime(buy_date_str, "%Y-%m-%d")

    # day before buy date
    before_date = prev_trading_day_before(trading_days, buy_date)

    # entry = next trading day
    entry_date = next_trading_day(trading_days, buy_date)

    # exit = prev trading day 1 month after entry
    target_exit = entry_date.replace(day=28) + timedelta(days=4)
    target_exit = target_exit.replace(day=1) - timedelta(days=1)
    exit_date = prev_trading_day(trading_days, target_exit)

    return before_date.date(), entry_date.date(), exit_date.date()
