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
            cache_path=".cache-spotify-test",
            show_dialog=True                   
        )
    )
