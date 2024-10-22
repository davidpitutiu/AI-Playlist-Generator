from flask import Flask, redirect, url_for, session, render_template, jsonify
import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import concurrent.futures
import time

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

    sp_oauth = SpotifyOAuth(client_id=cid, client_secret=secret, redirect_uri=redirect_uri, scope=scope)
    token_info = ensure_token_valid(sp_oauth)
    sp = spotipy.Spotify(auth=token_info['access_token'])

    try:
        print("Fetching all saved tracks...")
        all_saved_tracks = get_all_saved_tracks(sp)

        print(f"Number of saved tracks fetched: {len(all_saved_tracks)}")

        # Prepare to save track data
        track_data = []
        batch_size = 100  # Save every 100 tracks
        save_counter = 0
        total_tracks = len(all_saved_tracks)

        # Use concurrent futures for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_track_info = {executor.submit(get_track_info, item, token_info['access_token']): item for item in all_saved_tracks}
            for future in concurrent.futures.as_completed(future_to_track_info):
                try:
                    track_info = future.result()
                    track_data.append(track_info)
                    save_counter += 1

                    # Log each processed track
                    print(f"Processed track {save_counter}/{total_tracks}: {track_info['Track Name']} by {track_info['Artist']}")

                    # Batch save the data to reduce I/O operations
                    if save_counter % batch_size == 0 or save_counter == total_tracks:
                        save_partial_json(track_data)
                        print(f"Saved {save_counter}/{total_tracks} tracks so far.")

                except Exception as ex:
                    print(f"Error processing track: {str(ex)}")

        # Save complete data to JSON file once all tracks are processed
        with open('liked_songs.json', 'w', encoding='utf-8') as json_file:
            json.dump(track_data, json_file, ensure_ascii=False, indent=4)

        return jsonify({'num_tracks': len(track_data)})

    except Exception as e:
        print("Error occurred:", str(e))
        return jsonify({'error': str(e)}), 500

def save_partial_json(track_data):
    """ Save the track data incrementally to a JSON file """
    with open('liked_songs_partial.json', 'w', encoding='utf-8') as json_file:
        json.dump(track_data, json_file, ensure_ascii=False, indent=4)

# Helper function to get all saved tracks
def get_all_saved_tracks(spotify):
    saved_tracks = []
    offset = 0
    limit = 50  # Adjust this limit as needed
    while True:
        results = spotify.current_user_saved_tracks(limit=limit, offset=offset)
        saved_tracks.extend(results['items'])
        if len(results['items']) == 0:
            break
        offset += limit
    return saved_tracks

# Ensure token is valid
def ensure_token_valid(sp_oauth):
    token_info = session['token_info']
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
    return token_info


# artist_cache = {}  # Cache for artist genres

def get_track_info(track_item, access_token):
    """ Get simplified track info with Track Name, Artist, Release Date, Popularity, and Genre """
    track = track_item['track']
    track_name = track['name']
    artist_name = track['artists'][0]['name']
    release_date = track['album']['release_date']  # Retain release date
    popularity = track['popularity']
    # duration = track['duration']# Retain popularity
    duration_ms = track['duration_ms'] // 1000

    duration_formatted = f"{duration_ms // 60}:{duration_ms % 60:02d}"

    # Get the artist ID for retrieving genre info
    artist_id = track['artists'][0]['id']

    # Check if the genre info is already cached to avoid redundant API calls
    # if artist_id not in artist_cache:
    #     artist_info = spotipy.Spotify(auth=access_token).artist(artist_id)
    #     genres = ', '.join(artist_info['genres']) if artist_info['genres'] else 'N/A'
    #     artist_cache[artist_id] = genres
    # else:
    #     genres = artist_cache[artist_id]

    return {
        'Track Name': track_name,
        'Artist': artist_name,
        'Release Date': release_date,
        'Popularity': popularity,
        'Duration': duration_formatted,
    }

if __name__ == '__main__':
    app.run(port=8888, debug=True)
