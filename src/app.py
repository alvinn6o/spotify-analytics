'''
streamlit app

In recent time intervals: 1 month, 3 months, 12 months, all time
1a. display top 5 artists
1b. display top 5 tracks for an artist
2. display top 5 tracks
3. show total streaming time in bar chart per day during time interval
4. show total streaming time numeric
'''

import streamlit as st
import pandas as pd
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from data import load_json, filter_period
from stats import get_listening_time, get_listening_time_per_day, get_top_5_artists, get_top_5_songs, get_top_5_songs_artist

DATA_DIR = 'data'

@st.cache_data
def load_data() -> pd.DataFrame:
    df = load_json(DATA_DIR)
    return df

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

    # 1) If already authenticated, return client (refresh token if needed)
    if "spotify_token" in st.session_state:
        token_info = st.session_state["spotify_token"]
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info["refresh_token"])
            st.session_state["spotify_token"] = token_info
        return spotipy.Spotify(auth=token_info["access_token"])

    # 2) Read query params using the new API
    params = st.query_params
    code = params.get("code", None)

    # If Spotify redirected with a code, exchange it
    if code and "spotify_token" not in st.session_state:
        try:
            token_info = sp_oauth.get_access_token(code, as_dict=True)
            st.session_state["spotify_token"] = token_info

            # Clear query params from URL
            st.query_params.clear()

            return spotipy.Spotify(auth=token_info["access_token"])
        except Exception as e:
            st.error(f"Error during Spotify authentication: {e}")
            return None

    # 3) No auth yet → show login button
    auth_url = sp_oauth.get_authorize_url()
    st.info("To use live Spotify data, please log in with your Spotify account:")
    st.link_button("Log in", auth_url, type="primary")
    return None



def render_local_history_view():
    # Load local JSON data
    df = load_data(DATA_DIR)
    if df.empty:
        st.error(f"No data loaded from '{DATA_DIR}'. Make sure your JSON files are there.")
        return

    header_left, header_right = st.columns([3, 1])

    with header_left:
        st.subheader("Local Spotify stats (exported JSON)")

        st.subheader("Show past months:")
        interval_label = st.radio(
            "Select a time window:",
            options=["1 month", "3 months", "12 months", "all time"],
            horizontal=True,
            label_visibility="collapsed",
        )

    # Filter by period
    try:
        df_period = filter_period(df, interval_label)
    except Exception as e:
        st.error(f"Error filtering data for period '{interval_label}': {e}")
        return

    if df_period.empty:
        st.warning(f"No listening data found for interval: {interval_label}")
        return

    # Total listening time
    _, total_str = get_listening_time(df_period)

    with header_right:
        st.subheader("Total Listening Time")
        st.metric(
            label=f"Total streaming time ({interval_label})",
            value=total_str,
        )

    st.markdown("---")

    # Row 1: top artists, top tracks
    top_left, top_right = st.columns(2)

    with top_left:
        st.subheader("Top 5 Artists")

        top_artists = get_top_5_artists(df_period)
        st.dataframe(
            top_artists,
            use_container_width=True,
            hide_index=True,
        )

        artist_names = top_artists["Artist"].tolist() if not top_artists.empty else []

    with top_right:
        st.subheader(f"Top 5 Tracks in {interval_label}")

        top_tracks = get_top_5_songs(df_period)
        st.dataframe(
            top_tracks,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")

    # Row 2: artist-specific songs, weekday listening
    bottom_left, bottom_right = st.columns(2)

    with bottom_left:
        st.subheader("Top tracks by artist")

        if artist_names:
            selected_artist = st.selectbox(
                "Select artist for top tracks:",
                artist_names,
            )

            all_artist_songs = get_top_5_songs_artist(df_period)
            artist_songs = all_artist_songs[all_artist_songs["Artist"] == selected_artist]

            st.markdown(f"Top tracks for {selected_artist}:")
            st.dataframe(
                artist_songs,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("No artist data available for this interval.")

    with bottom_right:
        st.subheader("Listening Time by Weekday")

        weekday_stats = get_listening_time_per_day(df_period)

        if {"weekday", "Hours"}.issubset(weekday_stats.columns):
            chart_data = weekday_stats.set_index("weekday")["Hours"]
            st.bar_chart(chart_data)
        else:
            st.write("Unexpected columns from get_listening_time_per_day():")
            st.write(weekday_stats)


def render_mini_wrapped_view(sp):
    st.subheader("Spotify Mini Wrapped (API)")

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
        st.write("No artist data available from Spotify for this range.")
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

    # Sidebar mode selection
    mode = st.sidebar.radio(
        "Data source",
        options=["Local streaming export (JSON)", "Spotify Mini Wrapped (API)"],
    )

    st.markdown("---")

    if mode == "Local streaming export (JSON)":
        render_local_history_view()
    else:
        render_mini_wrapped_view(sp)




if __name__ == "__main__":
    main()