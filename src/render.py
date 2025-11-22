import streamlit as st
import spotipy
import pandas as pd

from stats import create_wrapped, fetch_recent_streams


def render_mini_wrapped_view(sp: spotipy.Spotify):
    st.subheader("Spotify Mini Wrapped")

    # ── Fetch data once ────────────────────────────────────────────────────────
    wrapped = create_wrapped(sp)
    recent_df = fetch_recent_streams(sp, limit=50)

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

    col_left, col_right = st.columns(2)

    # ───────────────────────── LEFT COLUMN ─────────────────────────────────────
    with col_left:
        st.markdown(f"### Top 5 artists ({time_label})")

        if artists_df.empty:
            st.write("No artist data for this range.")
            top5_artists = pd.DataFrame()
        else:
            artists = artists_df.copy()

            # If we have durations per track, approximate minutes per artist
            if (
                not tracks_df.empty
                and {"durationMs"}.issubset(tracks_df.columns)
            ):
                if "artistId" in tracks_df.columns and "artistId" in artists.columns:
                    # Use artistId if available
                    artist_time = (
                        tracks_df.groupby("artistId", as_index=False)["durationMs"]
                        .sum()
                        .rename(columns={"durationMs": "totalMs"})
                    )
                    artists = artists.merge(
                        artist_time,
                        on="artistId",
                        how="left",
                    )
                else:
                    # Fallback: group by artistName
                    artist_time = (
                        tracks_df.groupby("artistName", as_index=False)["durationMs"]
                        .sum()
                        .rename(columns={"durationMs": "totalMs"})
                    )
                    artists = artists.merge(
                        artist_time,
                        on="artistName",
                        how="left",
                    )

                artists["Minutes"] = (artists["totalMs"] / 1000 / 60).round().astype("Int64")
                artists.drop(columns=["totalMs"], inplace=True)
                artists["Minutes"] = artists["Minutes"].fillna(0)
            else:
                artists["Minutes"] = 0

            # Take top 5 by Minutes (then popularity as tie-breaker)
            artists = artists.sort_values(
                by=["Minutes", "popularity"],
                ascending=[False, False],
            )
            top5_artists = artists.head(5).copy()

            top5_artists.insert(0, "Rank", range(1, len(top5_artists) + 1))
            top5_artists.rename(columns={"artistName": "Artist"}, inplace=True)

            st.dataframe(
                top5_artists[["Rank", "Artist", "Minutes"]],
                use_container_width=True,
                hide_index=True,
            )

        # ── Top tracks for selected artist ─────────────────────────────────────
        st.markdown("Top songs for a selected artist")

        if not top5_artists.empty and not tracks_df.empty:
            # Build selection mapping. Prefer artistId if present.
            if "artistId" in top5_artists.columns:
                artist_options = {
                    row["Artist"]: row["artistId"]
                    for _, row in top5_artists.iterrows()
                }
                use_ids = True
            else:
                # Fallback: map by name only
                artist_options = {
                    row["Artist"]: row["Artist"]
                    for _, row in top5_artists.iterrows()
                }
                use_ids = False

            selected_name = st.selectbox(
                "Pick an artist:",
                options=list(artist_options.keys()),
                key=f"artist_select_{key}",
            )
            selected_key = artist_options[selected_name]

            # Filter tracks
            if use_ids and "artistId" in tracks_df.columns:
                artist_tracks = tracks_df[tracks_df["artistId"] == selected_key].copy()
            else:
                # Fallback: filter by artistName text
                artist_tracks = tracks_df[
                    tracks_df["artistName"].str.contains(
                        selected_name, case=False, na=False
                    )
                ].copy()

            if artist_tracks.empty:
                st.write("No tracks found for this artist in your top tracks.")
            else:
                artist_tracks["Minutes"] = (artist_tracks["durationMs"] / 1000 / 60).round(1)
                artist_tracks.rename(columns={"trackName": "Song"}, inplace=True)
                artist_tracks.sort_values("popularity", ascending=False, inplace=True)

                st.dataframe(
                    artist_tracks[["Song", "Minutes", "popularity"]].head(5),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.caption("Need both top artists and tracks to show artist songs.")

    # ───────────────────────── RIGHT COLUMN ────────────────────────────────────
    with col_right:
        st.markdown(f"### Top tracks ({time_label})")

        if tracks_df.empty:
            st.write("No track data for this range.")
        else:
            tracks = tracks_df.copy()
            tracks.insert(0, "Rank", range(1, len(tracks) + 1))
            tracks["Minutes"] = (tracks["durationMs"] / 1000 / 60).round(1)
            tracks.rename(
                columns={"trackName": "Song", "artistName": "Artist"},
                inplace=True,
            )

            top5_tracks = tracks.head(5)

            st.dataframe(
                top5_tracks[["Rank", "Song", "Artist", "Minutes", "popularity"]],
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("Show full top tracks list (up to 50)"):
                st.dataframe(
                    tracks[["Rank", "Song", "Artist", "Minutes", "popularity"]],
                    use_container_width=True,
                    hide_index=True,
                )

    # ───────────────────── Recently streamed songs ────────────────────────────
    st.markdown("---")
    st.subheader("Recently streamed songs")

    if recent_df.empty:
        st.write("No recent playback data available.")
    else:
        recent = recent_df.copy()
        recent["Minutes"] = (recent["msPlayed"] / 1000 / 60).round(1)
        recent.rename(
            columns={
                "endTime": "Played at",
                "artistName": "Artist",
                "trackName": "Song",
                "weekday": "Weekday",
            },
            inplace=True,
        )

        st.dataframe(
            recent[["Played at", "Artist", "Song", "Minutes", "Weekday"]],
            use_container_width=True,
            hide_index=True,
        )

    # ───────────────────── Total listening (approx) ───────────────────────────
    st.markdown("---")
    st.subheader("Approximate listening time (from top tracks)")

    if tracks_df.empty or "durationMs" not in tracks_df.columns:
        st.write("Not enough data to estimate listening time.")
    else:
        total_ms = tracks_df["durationMs"].sum()
        total_minutes = int(round(total_ms / 1000 / 60))
        st.metric("Total duration of your top tracks (minutes)", total_minutes)
        st.caption(
            "This sums the durations of your top tracks returned by Spotify for the "
            f"{time_label.lower()} range. "
            "Spotify's Web API does **not** expose full yearly listening time. "
            "For exact year stats, you’d need to use the exported streaming-history JSON."
        )
