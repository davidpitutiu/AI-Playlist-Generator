from flask import Flask, redirect, url_for, session, render_template, jsonify
import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Spotify API credentials
cid = 'b98f4b0dc951447c9cb3c2a7fe81c079'
secret = '5d505d2604fc455f880e11dbe86be26e'
redirect_uri = 'http://localhost:8888/callback'
scope = 'user-library-read'

@app.route('/')
def login():
    sp_oauth = SpotifyOAuth(client_id=cid, client_secret=secret, redirect_uri=redirect_uri, scope=scope)
    auth_url = sp_oauth.get_authorize_url()
    return render_template('login.html', auth_url=auth_url)

@app.route('/callback')
def callback():
    sp_oauth = SpotifyOAuth(client_id=cid, client_secret=secret, redirect_uri=redirect_uri, scope=scope)
    token_info = sp_oauth.get_access_token()
    session['token_info'] = token_info
    return redirect(url_for('home'))

@app.route('/home')
def home():
    if 'token_info' not in session:
        return redirect(url_for('login'))

    token_info = session['token_info']
    sp = spotipy.Spotify(auth=token_info['access_token'])
    all_saved_tracks = get_all_saved_tracks(sp)
    num_tracks = len(all_saved_tracks)

    return render_template('home.html', num_tracks=num_tracks)

@app.route('/start')
def start():
    if 'token_info' not in session:
        return redirect(url_for('login'))

    token_info = session['token_info']
    sp = spotipy.Spotify(auth=token_info['access_token'])

    try:
        # Get the list of saved tracks
        all_saved_tracks = get_all_saved_tracks(sp)

        # Prepare to save track data
        track_data = []
        for item in all_saved_tracks:
            track_info = get_track_info(item)
            track_data.append(track_info)

            # Simulate real-time updates
            save_partial_json(track_data)

        # Save complete data to JSON file
        with open('liked_songs.json', 'w', encoding='utf-8') as json_file:
            json.dump(track_data, json_file, ensure_ascii=False, indent=4)

        return jsonify({'num_tracks': len(track_data)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500  # Return an error if saving fails

def save_partial_json(track_data):
    """ Save the track data incrementally to a JSON file """
    with open('liked_songs_partial.json', 'w', encoding='utf-8') as json_file:
        json.dump(track_data, json_file, ensure_ascii=False, indent=4)

def get_all_saved_tracks(spotify):
    saved_tracks = []
    offset = 0
    limit = 50
    while True:
        results = spotify.current_user_saved_tracks(limit=limit, offset=offset)
        saved_tracks.extend(results['items'])
        if len(results['items']) == 0:
            break
        offset += limit
    return saved_tracks

def get_track_info(track_item):
    track = track_item['track']

    track_name = track['name']
    artist_name = track['artists'][0]['name']
    album_name = track['album']['name']
    release_date = track['album']['release_date']
    popularity = track['popularity']
    duration_ms = track['duration_ms'] // 1000

    artist_id = track['artists'][0]['id']
    artist_info = spotipy.Spotify(auth=session['token_info']['access_token']).artist(artist_id)
    genres = ', '.join(artist_info['genres']) if artist_info['genres'] else 'N/A'

    duration_formatted = f"{duration_ms // 60}:{duration_ms % 60:02d}"

    return {
        'Track Name': track_name,
        'Artist': artist_name,
        'Album': album_name,
        'Release Date': release_date,
        'Popularity': popularity,
        'Duration': duration_formatted,
        'Genres': genres
    }

if __name__ == '__main__':
    app.run(port=8888, debug=True)
