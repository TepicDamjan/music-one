from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

app = Flask(__name__)
CORS(app)

# Spotify API kljucevi
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')

# Spotify autentifikacija
auth_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

def is_spotify_url(url):
    """Provera da li je URL Spotify link"""
    return 'spotify.com' in url

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'MusicOne API is running'}), 200

# Preuzimanje podataka o pjesmi
@app.route('/song-info', methods=['POST'])
def song_info():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Url is required'}), 400

    url = data['url']

    try:
        if is_spotify_url(url):
            track_id = url.split("/")[-1].split("?")[0]
            track_info = sp.track(track_id)

            return jsonify({
                'name': track_info['name'],
                'artist': ', '.join(artist['name'] for artist in track_info['artists']),
                'album': track_info['album']['name'],
                'release_date': track_info['album']['release_date'],
                'duration_ms': track_info['duration_ms'],
                'album_image': track_info['album']['images'][0]['url'],
                'platform': 'spotify'
            }), 200
        else:
            return jsonify({'error': 'Unsupported URL. Please use Spotify links.'}), 400

    except Exception as e:
        print(f"Error fetching song info: {e}")
        return jsonify({'error': 'Failed to fetch song info'}), 500

# Skidanje pjesme
@app.route('/download', methods=['POST'])
def download_song():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    url = data['url']

    if not is_spotify_url(url):
        return jsonify({'error': 'Unsupported URL. Please use Spotify links.'}), 400

    try:
        print(f"Starting Spotify download for {url}")

        cmd = ['spotdl']

        # Dodaj config fajl ako postoji
        CONFIG_FILE = '/app/spotdl_config.json'
        if os.path.exists(CONFIG_FILE):
            print(f"Using spotdl config from {CONFIG_FILE}")
            cmd.extend(['--config', CONFIG_FILE])

        if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
            cmd.extend(['--client-id', SPOTIFY_CLIENT_ID, '--client-secret', SPOTIFY_CLIENT_SECRET])

        cmd.append(url)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=400)

        if result.returncode != 0:
            print(f"spotdl error: {result.stderr}")
            return jsonify({'error': f'Spotify download failed: {result.stderr[:200]}'}), 500

        return jsonify({'message': 'Download complete'}), 200

    except subprocess.CalledProcessError as e:
        print(f"Error during download: {e}")
        return jsonify({'error': 'Failed to download song'}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
