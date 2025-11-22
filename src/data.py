from typing import List
import pandas as pd
import os
from pathlib import Path


def count_json_files(directory_path: str | Path) -> int:
    count = 0

    try:
        for file in os.listdir(directory_path):
            file_path = os.path.join(directory_path, file)
            if file.lower().endswith('.json'):
                count += 1
    except Exception as e:
        print(f"Error counting JSON files: {e}")
        return 0
    
    return count
            


def load_json(directory_path: str | Path) -> pd.DataFrame:
    '''
    Loads all json files in /data into dataframe

    "endTime" : "2025-09-25 05:28",
    "artistName" : "Martin Garrix",
    "trackName" : "Scared to Be Lonely",
    "msPlayed" : 197508

    Columns: artistName, trackName, msPlayed, endTime

    returns df of all songs streamed in json files
    '''
    directory_path = Path(directory_path)

    json_count = count_json_files(directory_path)

    
    dfs: List[pd.DataFrame] = []

    for path in directory_path.glob('*.json'):
        df = pd.read_json(path)
        dfs.append(df)
    
    if not dfs:
        raise ValueError("No JSON files found")

    df = pd.concat(dfs, ignore_index=True)
    df['endTime'] = pd.to_datetime(df['endTime'])


    return df


def filter_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    '''
    intervals of last 1 month, 3 months, 12 months, all time
    '''

    if df.empty:
        raise ValueError("DataFrame is empty")

    if df['endTime'].dtype != 'datetime64[ns]':
        df['endTime'] = pd.to_datetime(df['endTime'])

    # remove timestamp with normalize
    max_date = df['endTime'].max().normalize()
    
    if period == '1 month':
        start_date = max_date - pd.DateOffset(months = 1)
    elif period == '3 months':
        start_date = max_date - pd.DateOffset(months = 3)
    elif period == '12 months':
        start_date = max_date - pd.DateOffset(months = 12)
    else:
        # all time interval
        return df

    return df[df['endTime'].dt.normalize() >= start_date]

