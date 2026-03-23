from functions import *

if __name__ == "__main__":
    sep_db_path = "./db_files/sep.duckdb"
    sf1_db_path = "./db_files/sf1_core.duckdb"
    meta_data_path = "./meta.csv"
    start_year = 2000
    end_year = 2026
    raw_yearly_data_path = "yearly_data"
    dates = generate_monthly_dates(start_year, end_year)
    for year, dates_list in dates.items():
        year_dfs = []
        trading_days = load_trading_calendar()
        for d in dates_list:
            print(f"\nProcessing date {d}...")
            before_date, buy_date, sell_date = get_value_dates(d, trading_days)
            df = get_three_date_prices(sep_db_path, before_date, buy_date, sell_date)
            df = get_fundementals_for_dates(df, sf1_db_path, meta_data_path)
            year_dfs.append(df)
        final_year_df = pd.concat(year_dfs, ignore_index=True)
        final_year_df.to_csv(
            f"./{raw_yearly_data_path}/value_ps_1m_monthly_sep_{year}.csv",
            index=False,
        )
        print(
            f"\n✅ Done. Saved to ./{raw_yearly_data_path}/value_ps_1m_monthly_sep_{year}.csv"
        )
