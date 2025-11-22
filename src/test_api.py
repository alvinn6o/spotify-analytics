import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
from stats import *

SCOPES = "user-read-recently-played user-top-read"

def get_sp():
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=st.secrets["SPOTIFY_CLIENT_ID"],
            client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
            scope=SCOPES,
            cache_path=".cache-spotify-test",  # optional, keeps test separate
            show_dialog=True                    # forces re-consent sometimes
        )
    )



def main():
    st.title("Test Spotify API Locally")

    sp = get_sp()

    st.write("📡 Calling Spotify API...")
    df = fetch_top_artists(sp, limit=50, time_range='long_term')

    st.subheader("Result:")
    st.dataframe(df, use_container_width=True)

    st.write("Number of rows:", df.shape[0])


if __name__ == "__main__":
    main()