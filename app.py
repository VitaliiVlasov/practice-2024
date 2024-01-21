from flask import Flask, render_template, redirect, request, url_for, session
import spotipy
import os
from datetime import datetime

from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)

SPOTIFY_CLIENT_ID = 'test'
SPOTIFY_CLIENT_SECRET = 'test'
SPOTIFY_REDIRECT_URI = 'https://spotify.kartew.dev/callback'
SPOTIFY_SCOPE = "user-library-read,user-read-recently-played"

app.secret_key = os.urandom(24)

# Setup Spotify OAuth
sp_oauth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                        client_secret=SPOTIFY_CLIENT_SECRET,
                        redirect_uri=SPOTIFY_REDIRECT_URI,
                        scope=SPOTIFY_SCOPE)


@app.route('/')
def index():
    logged_in = 'token_info' in session
    if logged_in:
        token_info = session['token_info']
        sp = spotipy.Spotify(auth=token_info['access_token'])
        results = sp.current_user_recently_played(limit=10)

        # Create a list of song dictionaries containing the required details
        recently_played_tracks = [
            {
                'title': item['track']['name'],
                'artist': ', '.join(artist['name'] for artist in item['track']['artists']),
                'album': item['track']['album']['name'],
                'played_at': item['played_at'],
                'duration': item['track']['duration_ms']
            }
            for item in results['items']
        ]

        return render_template('index.html', logged_in=logged_in, recently_played_tracks=recently_played_tracks)
    else:
        return render_template('index.html', logged_in=logged_in)


@app.template_filter('dateformat')
def dateformat(value, format='%Y-%m-%d %H:%M'):
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ').strftime(format)


@app.template_filter('durationformat')
def durationformat(value):
    minutes, milliseconds = divmod(value, 60000)
    seconds = float(milliseconds) / 1000
    return f"{int(minutes)}:{int(seconds):02d}"


@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info

    sp = spotipy.Spotify(auth=token_info['access_token'])
    recently_played = sp.current_user_recently_played(limit=10)

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/statistics')
def statistics():
    logged_in = 'token_info' in session
    if not logged_in:
        return redirect(url_for('login'))

    token_info = session['token_info']
    sp = spotipy.Spotify(auth=token_info['access_token'])

    # Fetch and sort the top artists from Spotify
    top_artists_data = sp.current_user_top_artists(limit=10)
    top_artists = sorted(top_artists_data['items'], key=lambda a: a['popularity'], reverse=True)
    artist_names = [artist['name'] for artist in top_artists]
    artist_popularity = [artist['popularity'] for artist in top_artists]

    # Fetch and sort the top tracks from Spotify
    top_tracks_data = sp.current_user_top_tracks(limit=10)
    top_tracks = sorted(top_tracks_data['items'], key=lambda t: t['popularity'], reverse=True)
    track_names = [track['name'] for track in top_tracks]
    track_play_counts = [track['popularity'] for track in top_tracks]

    # Aggregate and sort the genres
    genres = {}
    for artist in top_artists_data['items']:
        for genre in artist['genres']:
            genres[genre] = genres.get(genre, 0) + 1
    sorted_genres = sorted(genres.items(), key=lambda item: item[1], reverse=True)
    genre_names = [genre[0] for genre in sorted_genres[:10]]
    genre_counts = [genre[1] for genre in sorted_genres[:10]]

    return render_template('statistics.html',
                           genre_names=genre_names,
                           genre_counts=genre_counts,
                           artist_names=artist_names,
                           artist_popularity=artist_popularity,
                           track_names=track_names,
                           track_play_counts=track_play_counts)


@app.route('/policy')
def policy():
    return render_template('policy.html')


if __name__ == '__main__':
    app.run(port=8080, host='0.0.0.0')
