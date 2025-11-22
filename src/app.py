import streamlit as st
import pandas as pd
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from data import load_json, filter_period
from stats import create_wrapped

DATA_DIR = 'data'

'''
@st.cache_data
def load_data() -> pd.DataFrame:
    df = load_json(DATA_DIR)
    return df
'''

SCOPES = "user-read-email user-top-read user-read-recently-played"

def get_spotify_client() -> spotipy.Spotify | None:
    """
    Handle Spotify OAuth and return an authenticated Spotipy client.
    """

    sp_oauth = SpotifyOAuth(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=st.secrets["SPOTIFY_REDIRECT_URI"],
        scope=SCOPES,
    )

    if "spotify_token" in st.session_state:
        token_info = st.session_state["spotify_token"]
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
            st.session_state["spotify_token"] = token_info
        return spotipy.Spotify(auth=token_info["access_token"])

    params = st.query_params
    raw = params.get("code", None)
    code = None
    if isinstance(raw, list) and raw:
        code = raw[0]
    elif isinstance(raw, str):
        code = raw

    if code and "spotify_token" not in st.session_state:
        try:
            token_info = sp_oauth.get_access_token(code, as_dict=True)
            st.session_state["spotify_token"] = token_info
            st.query_params.clear()

            return spotipy.Spotify(auth=token_info["access_token"])

        except Exception as e:
            st.error(f"Error during Spotify authentication: {e}")
            return None

    auth_url = sp_oauth.get_authorize_url()
    st.info("Log in with spotify:")
    st.link_button("Log in", auth_url, type="primary")
    return None



def render_mini_wrapped_view(sp):
    st.subheader("Spotify Mini Wrapped")

    wrapped = create_wrapped(sp)

    range_map = {
        "short": "Last 4 weeks",
        "medium": "Last 6 months",
        "long": "Several years",
    }

    label_to_key = {
        "Last 4 weeks": "short",
        "Last 6 months": "medium",
        "Several years": "long",
    }

    time_label = st.selectbox(
        "Select time range:",
        options=list(label_to_key.keys()),
    )

    key = label_to_key[time_label]
    entry = wrapped.get(key, {})

    artists_df = entry.get("artists", pd.DataFrame())
    tracks_df = entry.get("tracks", pd.DataFrame())

    st.subheader(f"Top artists ({time_label})")
    if artists_df.empty:
        st.write("Data unavailable.")
    else:
        st.dataframe(
            artists_df,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")

    st.subheader(f"Top tracks ({time_label})")
    if tracks_df.empty:
        st.write("No track data available from Spotify for this range.")
    else:
        display_cols = [
            "trackName",
            "artistName",
            "durationMs",
            "popularity",
            "danceability",
            "energy",
            "valence",
            "tempo",
        ]
        display_cols = [c for c in display_cols if c in tracks_df.columns]

        st.dataframe(
            tracks_df[display_cols],
            use_container_width=True,
            hide_index=True,
        )


def main():
    st.set_page_config(page_title="Spotify Analytics", layout="wide")

    # Authenticate with Spotify
    sp = get_spotify_client()
    if sp is None:
        st.stop()

    user = sp.current_user()
    display_name = user.get("display_name", "Spotify user")
    st.success(f"{display_name} logged in")

    st.markdown("---")

    render_mini_wrapped_view(sp)




if __name__ == "__main__":
    main()