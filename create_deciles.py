import glob
from functions import create_top_and_bottom_deciles

yearly_data_files = glob.glob("./yearly_data/*.csv")
top_decile_path = "./years_top_deciles/"
bottom_decile_path = "./years_bottom_deciles/"
for file in yearly_data_files:
    create_top_and_bottom_deciles(
        file,
        top_decile_path,
        bottom_decile_path,
    )
