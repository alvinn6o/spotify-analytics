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

from data import load_json, filter_period
from stats import get_listening_time, get_listening_time_per_day, get_top_5_artists, get_top_5_songs, get_top_5_songs_artist

DATA_DIR = 'data'

@st.cache_data
def load_data() -> pd.DataFrame:
    df = load_json(DATA_DIR)
    return df


def main():
    st.set_page_config(page_title="Spotify Analytics", layout="wide")

    df = load_data()
    if df.empty:
        st.error(f"No data loaded from '{DATA_DIR}'. Make sure your JSON files are there.")
        return

    # ---------- HEADER ROW: title + interval + total time metric ----------
    header_left, header_right = st.columns([3, 1])

    with header_left:
        st.title("Alvin's Spotify Stats")

        st.subheader("Show past months:")
        interval_label = st.radio(
            "Select a time window:",
            options=["1 month", "3 months", "12 months", "all time"],
            horizontal=True,
            label_visibility="collapsed",  # hides the small label text
        )

    # filter after we know interval_label
    try:
        df_period = filter_period(df, interval_label)
    except Exception as e:
        st.error(f"Error filtering data for period '{interval_label}': {e}")
        return

    if df_period.empty:
        st.warning(f"No listening data found for interval: {interval_label}")
        return

    # compute total listening time for metric
    _, total_str = get_listening_time(df_period)

    with header_right:
        st.subheader("Total Listening Time")
        st.metric(
            label=f"Total streaming time ({interval_label})",
            value=total_str,
        )

    st.markdown("---")

    # ---------- ROW 1 (TOP QUADRANTS): Top artists & top tracks ----------
    top_left, top_right = st.columns(2)

    # Q1: Top 5 Artists
    with top_left:
        st.subheader("Top 5 Artists")

        top_artists = get_top_5_artists(df_period)
        st.dataframe(
            top_artists,
            use_container_width=True,
            hide_index=True,
        )

        artist_names = top_artists["Artist"].tolist() if not top_artists.empty else []

    # Q2: Top 5 Tracks overall
    with top_right:
        st.subheader(f"Top 5 Tracks in {interval_label}")

        top_tracks = get_top_5_songs(df_period)
        st.dataframe(
            top_tracks,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")

    # ---------- ROW 2 (BOTTOM QUADRANTS): tracks per artist & weekday chart ----------
    bottom_left, bottom_right = st.columns(2)

    # Q3: Top 5 tracks for selected artist
    with bottom_left:
        st.subheader("Top tracks by artist")

        if artist_names:
            selected_artist = st.selectbox(
                "Select artist for top tracks:",
                artist_names,
            )

            all_artist_songs = get_top_5_songs_artist(df_period)
            artist_songs = all_artist_songs[all_artist_songs["Artist"] == selected_artist]

            st.markdown(f"**Top tracks for {selected_artist}:**")
            st.dataframe(
                artist_songs,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("No artist data available for this interval.")

    # Q4: Listening Time by Weekday (bar chart)
    with bottom_right:
        st.subheader("Listening Time by Weekday")

        weekday_stats = get_listening_time_per_day(df_period)

        # Expecting at least ['weekday', 'Hours'] from your function
        if {"weekday", "Hours"}.issubset(weekday_stats.columns):
            chart_data = weekday_stats.set_index("weekday")["Hours"]
            st.bar_chart(chart_data)
        else:
            st.write("Unexpected columns from get_listening_time_per_day():")
            st.write(weekday_stats)


if __name__ == "__main__":
    main()