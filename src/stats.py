from utils import format_time
from data import load_json, filter_period

import pandas as pd
from typing import List, Tuple
from spotipy import SpotifyException


def fetch_recent_streams(sp, limit: int = 50) -> pd.DataFrame:
    '''
    fetch the most recent 50 streams for the user and turn into
    pd data frame
    '''

    fetched = sp.current_user_recently_played(limit=limit)

    streams = []
    for item in fetched.get('items', []):
        played_at = pd.to_datetime(item['played_at'])
        track = item['track']

        track_name = track['name']
        artist = track['artists'][0] if track['artists'] else {}
        artist_name = artist.get('name', 'NA')
        artist_id = artist.get('id')
        ms_played = track.get('duration_ms', 0)

        streams.append(
            {
                'endTime' : played_at,
                'artistName' : artist_name,
                'trackName' : track_name,
                'msPlayed' : ms_played,
                'artistId' : artist_id
            }
        )
    
    df = pd.DataFrame(streams)
    if not df.empty:
        df['weekday'] = df['endTime'].dt.day_name()

    return df


def fetch_top_artists(sp, limit=50, time_range='long_term'):

    fetched = sp.current_user_top_artists(limit=limit, time_range=time_range)

    artists = []
    for artist in fetched.get('items', []):
        artists.append(
            {
                'artistId' : artist['id'],
                'artistName' : artist['name'],
                'popularity' : artist['popularity'],
                'genres' : ', '.join(artist.get('genres', [])),
            }
        )
    
    df = pd.DataFrame(artists)
    return df

def fetch_top_tracks(sp, limit=50, time_range='long_term'):

    fetched = sp.current_user_top_tracks(limit=limit, time_range=time_range)

    tracks = []

    for track in fetched.get('items', []):
        tracks.append({
            'trackId' : track['id'],
            'trackName' : track['name'],
            'artistName' : ', '.join(artist['name'] for artist in track['artists']),
            'durationMs' : track['duration_ms'],
            'popularity' : track['popularity']
        })
    
    df = pd.DataFrame(tracks)
    return df


def fetch_audio_features(sp, df_tracks: pd.DataFrame) -> pd.DataFrame:
    """
    Fetch audio features in batches and merge them back into df_tracks.
    If Spotify rejects the request (403, etc.), return df_tracks unchanged
    and show a friendly message instead of crashing the app.
    """
    if df_tracks.empty or "trackId" not in df_tracks.columns:
        return df_tracks

    track_ids = df_tracks["trackId"].dropna().unique().tolist()
    if not track_ids:
        return df_tracks

    all_features = []
    BATCH_SIZE = 50  # safe batch size

    import streamlit as st  # import once here

    for i in range(0, len(track_ids), BATCH_SIZE):
        batch_ids = track_ids[i : i + BATCH_SIZE]
        try:
            features = sp.audio_features(batch_ids)
        except Exception as e:
            # Catch *anything* from this call so it never kills the app
            st.warning(
                "Could not load audio features from Spotify. "
                "Showing top tracks without danceability/energy/valence/tempo."
            )
            # Optional: log details to server logs only
            # print(f"audio_features error: {e}")
            return df_tracks

        if features:
            all_features.extend([f for f in features if f is not None])

    if not all_features:
        return df_tracks

    df_features = pd.DataFrame(all_features)[[
        "id",
        "danceability",
        "energy",
        "valence",
        "tempo",
        "acousticness",
        "instrumentalness",
        "liveness",
        "speechiness",
    ]]

    df_features.rename(columns={"id": "trackId"}, inplace=True)

    df_merged = df_tracks.merge(df_features, on="trackId", how="left")
    return df_merged



def create_wrapped(sp):
    time_ranges = {
        'short' : 'short_term',
        'medium' : 'medium_term',
        'long' : 'long_term'
    }

    wrapped = {}

    for entry, range in time_ranges.items():
        # get artists and tracks fro each time range
        artists = fetch_top_artists(sp, limit=50, time_range=range)
        tracks = fetch_top_tracks(sp, limit=50, time_range=range)
        tracks = fetch_audio_features(sp, tracks)

        wrapped[entry] = {
            'artists' : artists,
            'tracks' : tracks
        }
    
    return wrapped


'''
Below are functions used in initial testing with personal data
'''
        

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

    weekday_avg = daily_totals.groupby('weekday', as_index=False)['msPlayed'].mean()

    weekday_avg['Hours'] = (weekday_avg['msPlayed'] / 1000 / 60 / 60).round(2)

    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    weekday_avg['weekday'] = pd.Categorical(weekday_avg['weekday'], categories=days, ordered=True)
    weekday_avg = weekday_avg.sort_values('weekday')

    return weekday_avg



