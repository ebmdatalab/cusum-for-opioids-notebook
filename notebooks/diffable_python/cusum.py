# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: all
#     notebook_metadata_filter: all,-language_info
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.3.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

import pandas as pd
from lib.cusum import most_change_against_window
from ebmdatalab import bq 

sql = """
SELECT
  pct_id,
  percentile
FROM measures.ccg_data_opioidper1000
"""
df = bq.cached_read(sql, csv_path='ccg_percentiles.zip')

for pct_id, grouped in df.groupby("pct_id"):
    changes = most_change_against_window(grouped.percentile, window=12)
    if changes['improvements']:
        print(pct_id, changes['improvements'])

sql = """
SELECT
  practice_id,
  percentile
FROM measures.practice_data_opioidper1000
"""
df2 = bq.cached_read(sql, csv_path='practice_percentiles.zip')

practice_df = pd.DataFrame(columns=["practice_id", "from", "to", "period"])
for practice_id, grouped in df2.groupby("practice_id"):
    changes = most_change_against_window(grouped.percentile, window=24)
    improvements = changes['improvements'] and changes['improvements'][0] or {}
    if improvements.get("to", 0) > 0:
        practice_df = practice_df.append([{ 'practice_id': practice_id, 'from': improvements["from"], 'to': improvements["to"], 'period': improvements["period"]}])

#https://openprescribing.net/measure/opioidper1000/practice/{}/"
practice_df['delta'] = practice_df["from"] - practice_df["to"]
practice_df = practice_df.sort_values("delta", ascending=False)
practice_df[practice_df.period > 1]
