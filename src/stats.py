from utils import format_time
from data import load_json, filter_period

import pandas as pd
from typing import List, Tuple


def get_top_5_artists(df: pd.DataFrame) -> pd.DataFrame:
    '''
    return top 5 artists with stteaming time
    '''

    top_5_artists = df.groupby('artistName', as_index=False)['msPlayed'].sum().sort_values(by='msPlayed', ascending=False).head(5)

    top_5_artists['minutes'] = (top_5_artists['msPlayed'] / 1000 / 60).round().astype(int)
    top_5_artists.drop(columns=['msPlayed'], inplace=True)

    top_5_artists.rename(columns={'artistName': 'Artist'}, inplace=True)
    top_5_artists.reset_index(drop=True, inplace=True)

    return top_5_artists

def get_top_5_songs_artist(df: pd.DataFrame) -> pd.DataFrame:

    '''
    for top 5 artists, return their top 5 songs
    '''
    top_5_artists = get_top_5_artists(df)['Artist'].tolist()

    df_top_artists = df[df['artistName'].isin(top_5_artists)].copy()

    buckets = df_top_artists.groupby(['artistName', 'trackName'], as_index=False)['msPlayed'].sum()
    buckets.reset_index(drop=True, inplace=True)

    top_songs = buckets.sort_values(['artistName', 'msPlayed'], ascending=[True, False]).groupby('artistName').head(5)
    
    top_songs['minutes'] = (top_songs['msPlayed'] / 1000 / 60).round().astype(int)
    top_songs.drop(columns=['msPlayed'], inplace=True)

    top_songs['artistName'] = pd.Categorical(
        top_songs['artistName'],
        categories=top_5_artists,
        ordered=True
    )
    top_songs = top_songs.sort_values(['artistName', 'minutes'], ascending=[True, False])




    top_songs.rename(columns= {'artistName' : 'Artist' , 'trackName' : 'Song'}, inplace=True)
    top_songs.reset_index(drop=True, inplace=True)


    return top_songs

def get_top_5_songs(df: pd.DataFrame) -> pd.DataFrame:
    '''
    return top 5 songs of all time (not by artist) by streaming time

    1. group by tracks and sum
    2. order the list
    3. select 5 from from list
    4. format

    '''

    top_5_songs = df.groupby(['artistName', 'trackName'], as_index=False)['msPlayed'].sum().sort_values(by='msPlayed', ascending=False).head(5)

    top_5_songs['minutes'] = (top_5_songs['msPlayed'] / 1000 / 60).round().astype(int)

    top_5_songs.rename(columns= {'artistName' : 'Artist' , 'trackName' : 'Song'}, inplace=True)
    top_5_songs.drop(columns=['msPlayed'], inplace=True)
    top_5_songs.reset_index(drop=True, inplace=True)

    return top_5_songs

def get_listening_time(df: pd.DataFrame) -> Tuple[int, str]:
    '''
    return total listening time in ms and days:hours:min format
    '''
    total_ms = int(df['msPlayed'].sum())
    total_formatted = format_time(total_ms)

    return total_ms, total_formatted




def get_listening_time_per_day(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return average listening time in HOURS per weekday.
    """

    df = df.copy()
    df['date'] = df['endTime'].dt.date
    df['weekday'] = df['endTime'].dt.day_name()

    # total listening per actual day
    daily_totals = df.groupby(['date', 'weekday'], as_index=False)['msPlayed'].sum()

    # now average those totals by weekday
    weekday_avg = daily_totals.groupby('weekday', as_index=False)['msPlayed'].mean()

    # convert ms → hours
    weekday_avg['Hours'] = (weekday_avg['msPlayed'] / 1000 / 60 / 60).round(2)

    # reorder weekdays
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    weekday_avg['weekday'] = pd.Categorical(weekday_avg['weekday'], categories=days, ordered=True)
    weekday_avg = weekday_avg.sort_values('weekday')

    return weekday_avg



