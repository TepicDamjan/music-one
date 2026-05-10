from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import json

app = Flask(__name__)
CORS(app)

# Spotify API kljucevi
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')

# Direktorijum za preuzimanje (lokalno: ~/Music/MusicOne, Docker: /app/downloads)
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', os.path.expanduser('~/Music/MusicOne'))
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
print(f"Downloads will be saved to: {DOWNLOAD_DIR}")

# Spotify autentifikacija
auth_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

def is_spotify_url(url):
    """Provera da li je URL Spotify link"""
    return 'spotify.com' in url

def is_youtube_url(url):
    """Provera da li je URL YouTube link"""
    return 'youtube.com' in url or 'youtu.be' in url

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
    fmt = data.get('format', 'mp3').lower()

    SPOTIFY_FORMATS = ['mp3', 'flac']
    if fmt not in SPOTIFY_FORMATS:
        return jsonify({'error': f'Spotify podrzava samo: {", ".join(SPOTIFY_FORMATS)}'}), 400

    if not is_spotify_url(url):
        return jsonify({'error': 'Unsupported URL. Please use Spotify links.'}), 400

    try:
        print(f"Starting Spotify download for {url} [{fmt}]")

        cmd = ['spotdl']

        # Dodaj config fajl ako postoji (Docker ili lokalni)
        CONFIG_FILE = '/app/spotdl_config.json'
        LOCAL_CONFIG = os.path.join(os.path.dirname(__file__), 'spotdl_config.json')
        if os.path.exists(CONFIG_FILE):
            print(f"Using spotdl config from {CONFIG_FILE}")
            cmd.extend(['--config', CONFIG_FILE])
        elif os.path.exists(LOCAL_CONFIG):
            print(f"Using local spotdl config from {LOCAL_CONFIG}")
            cmd.extend(['--config', LOCAL_CONFIG])

        # Format i output
        cmd.extend(['--format', fmt])
        cmd.extend(['--output', DOWNLOAD_DIR])

        if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
            cmd.extend(['--client-id', SPOTIFY_CLIENT_ID, '--client-secret', SPOTIFY_CLIENT_SECRET])

        cmd.append(url)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=400)

        if result.returncode != 0:
            print(f"spotdl error: {result.stderr}")
            return jsonify({'error': f'Spotify download failed: {result.stderr[:200]}'}), 500

        return jsonify({'message': f'Download complete ({fmt.upper()})', 'saved_to': DOWNLOAD_DIR}), 200

    except subprocess.CalledProcessError as e:
        print(f"Error during download: {e}")
        return jsonify({'error': 'Failed to download song'}), 500

# Info o YouTube videu/playlisti
@app.route('/youtube-info', methods=['POST'])
def youtube_info():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    url = data['url']

    if not is_youtube_url(url):
        return jsonify({'error': 'Unsupported URL. Please use YouTube links.'}), 400

    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-playlist',   # samo prvi video ako je playlist
            '--flat-playlist',
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return jsonify({'error': f'Could not fetch video info: {result.stderr[:200]}'}), 500

        # Uzmi prvu liniju JSON-a (prvi video)
        first_line = result.stdout.strip().split('\n')[0]
        info = json.loads(first_line)

        is_playlist = 'playlist' in url or 'list=' in url

        return jsonify({
            'name': info.get('title', 'Nepoznat naslov'),
            'artist': info.get('uploader', info.get('channel', 'Nepoznat kanal')),
            'album': 'YouTube',
            'release_date': info.get('upload_date', ''),
            'duration_ms': (info.get('duration', 0) or 0) * 1000,
            'album_image': info.get('thumbnail', ''),
            'platform': 'youtube',
            'is_playlist': is_playlist
        }), 200

    except Exception as e:
        print(f"Error fetching YouTube info: {e}")
        return jsonify({'error': 'Failed to fetch YouTube info'}), 500


# Skidanje YouTube videa/playliste
@app.route('/download-youtube', methods=['POST'])
def download_youtube():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    url = data['url']
    fmt = data.get('format', 'mp3').lower()

    YOUTUBE_FORMATS = ['mp3', 'flac', 'mp4']
    if fmt not in YOUTUBE_FORMATS:
        return jsonify({'error': f'Podrzani formati: {", ".join(YOUTUBE_FORMATS)}'}), 400

    if not is_youtube_url(url):
        return jsonify({'error': 'Unsupported URL. Please use YouTube links.'}), 400

    try:
        print(f"Starting YouTube download for {url} [{fmt}]")
        print(f"Saving to: {DOWNLOAD_DIR}")

        output_template = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')

        if fmt == 'mp4':
            # Video + audio, spoji u MP4
            cmd = [
                'yt-dlp',
                '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--merge-output-format', 'mp4',
                '--add-metadata',
                '--embed-thumbnail',
                '-o', output_template,
                url
            ]
        else:
            # Audio only: mp3 ili flac
            cmd = [
                'yt-dlp',
                '-x',
                '--audio-format', fmt,
                '--audio-quality', '0',      # Najbolji kvalitet
                '--add-metadata',
                '--embed-thumbnail',
                '-o', output_template,
                url
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            print(f"yt-dlp error: {result.stderr}")
            return jsonify({'error': f'YouTube download failed: {result.stderr[:200]}'}), 500

        return jsonify({
            'message': f'YouTube download complete ({fmt.upper()})',
            'saved_to': DOWNLOAD_DIR
        }), 200

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Download timed out'}), 504
    except Exception as e:
        print(f"Error during YouTube download: {e}")
        return jsonify({'error': 'Failed to download from YouTube'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
