from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import json
import re
from googleapiclient.discovery import build
from datetime import datetime

app = Flask(__name__)
CORS(app)

#Spotify API kljucevi
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')

# YouTube API key
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')

# YouTube cookies from environment variable (preferred method)
YOUTUBE_COOKIES = os.environ.get('YOUTUBE_COOKIES', '')

# Remove file-based cookies handling since we're using environment variables
print("Using environment variable for YouTube cookies" if YOUTUBE_COOKIES else "No cookies provided, using default authentication")

#Spotify autentifikacija
auth_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager = auth_manager)

def is_youtube_url(url):
    """Provera da li je URL YouTube link"""
    return 'youtube.com' in url or 'youtu.be' in url

def is_spotify_url(url):
    """Provera da li je URL Spotify link"""
    return 'spotify.com' in url

def extract_youtube_video_id(url):
    """Izvlači video ID iz YouTube URL-a"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([\w-]+)',
        r'(?:youtu\.be\/)([\w-]+)',
        r'(?:youtube\.com\/embed\/)([\w-]+)',
        r'(?:youtube\.com\/v\/)([\w-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_video_info_api(video_id):
    """Koristi YouTube Data API v3 za dobijanje informacija"""
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        request = youtube.videos().list(
            part='snippet,contentDetails',
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            return None
            
        video = response['items'][0]
        snippet = video['snippet']
        
        # Parse ISO 8601 duration (PT1H2M10S -> seconds)
        duration_str = video['contentDetails']['duration']
        duration_seconds = parse_iso_duration(duration_str)
        
        return {
            'name': snippet['title'],
            'artist': snippet['channelTitle'],
            'album': 'YouTube Video',
            'release_date': snippet['publishedAt'][:10],
            'duration_ms': duration_seconds * 1000,
            'album_image': snippet['thumbnails'].get('high', {}).get('url', ''),
            'platform': 'youtube'
        }
    except Exception as e:
        print(f"YouTube API error: {e}")
        return None

def parse_iso_duration(duration):
    """Parsira ISO 8601 duration format (PT1H2M10S) u sekunde"""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    return hours * 3600 + minutes * 60 + seconds

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    youtube_api_status = "with YouTube API" if YOUTUBE_API_KEY else "with yt-dlp only"
    return jsonify({
        'status': 'ok', 
        'message': f'MusicOne API is running {youtube_api_status}'
    }), 200

#preuzimanje podataka o pjesmi
@app.route('/song-info', methods=['POST'])
def song_info():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error':'Url is required'}),400
    
    url = data['url']
    
    try:
        if is_spotify_url(url):
            # Spotify logic
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
            }),200
            
        elif is_youtube_url(url):
            # YouTube hybrid approach: API first, then yt-dlp fallback
            video_id = extract_youtube_video_id(url)
            
            if not video_id:
                return jsonify({'error': 'Invalid YouTube URL'}), 400
            
            # Try YouTube Data API first (fast and reliable)
            if YOUTUBE_API_KEY:
                print(f"Trying YouTube Data API for video: {video_id}")
                info = get_youtube_video_info_api(video_id)
                if info:
                    return jsonify(info), 200
                print("YouTube API failed, falling back to yt-dlp...")
            
            # Fallback to yt-dlp if API not available or failed
            print("Using yt-dlp for metadata extraction...")
            result = subprocess.run(
                ['yt-dlp', 
                 '--dump-json', 
                 '--no-playlist', 
                 '--no-warnings',
                 '--extractor-args', 'youtube:player_client=android',
                 '--user-agent', 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip',
                 url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"yt-dlp error: {result.stderr}")
                return jsonify({'error': f'YouTube video info failed: {result.stderr}'}), 500
            
            video_info = json.loads(result.stdout)
            
            return jsonify({
                'name': video_info.get('title', 'Unknown'),
                'artist': video_info.get('uploader', 'Unknown'),
                'album': 'YouTube Video',
                'release_date': video_info.get('upload_date', 'Unknown'),
                'duration_ms': int(video_info.get('duration', 0)) * 1000,
                'album_image': video_info.get('thumbnail', ''),
                'platform': 'youtube'
            }),200
        else:
            return jsonify({'error': 'Unsupported URL. Please use Spotify or YouTube links.'}), 400
            
    except Exception as e:
        print(f"Error fetching song info: {e}")
        return jsonify({'error': 'Failed to fetch song info'}), 500

def get_yt_dlp_base_args(include_format=True, audio_only=False):
    """Vraća osnovne argumente za yt-dlp sa opcionalnim cookies"""
    base_args = [
        'yt-dlp',
        '--no-playlist',
        '--no-warnings',
        '--no-check-certificates',  # Ignoriši SSL greške
        '--extractor-args', 'youtube:player_client=android,ios',
        '--user-agent', 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip'
    ]
    
    # Za audio download ne koristimo --format, jer -x automatski bira najbolji audio
    if include_format and not audio_only:
        base_args.extend(['--format', 'best', '--skip-unavailable-fragments'])
    
    # Koristi cookies iz environment varijable ako postoje
    if YOUTUBE_COOKIES:
        print("Using cookies from environment variable")
        # Sačuvaj cookies u privremeni fajl
        import tempfile
        import atexit
        import os
        cookies_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        cookies_file.write(YOUTUBE_COOKIES)
        cookies_file.close()
        base_args.extend(['--cookies', cookies_file.name])
        # Automatsko brisanje fajla kada se završi
        def cleanup_temp_file():
            try:
                os.unlink(cookies_file.name)
            except:
                pass
        atexit.register(cleanup_temp_file)
    else:
        print("No cookies provided, using default authentication")
    
    return base_args

#skidanje pjesme
@app.route('/download', methods=['POST'])
def download_song():
    data = request.get_json()  
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    url = data['url']

    try:
        print(f"Starting download for {url}")
        
        if is_spotify_url(url):
            # Koristi spotdl za Spotify
            result = subprocess.run(['spotdl', url], capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                print(f"spotdl error: {result.stderr}")
                return jsonify({'error': f'Spotify download failed: {result.stderr[:200]}'}), 500
        elif is_youtube_url(url):
            # Koristi yt-dlp za YouTube - preuzmi kao mp3
            # Koristi sistemski FFmpeg (instaliran u Dockerfile)
            result = subprocess.run([
                'yt-dlp',
                '-x',  # Extract audio
                '--audio-format', 'mp3',
                '--audio-quality', '0',  # Best quality
                '--no-playlist',
                '--no-warnings',
                '--extractor-args', 'youtube:player_client=android',
                '--user-agent', 'com.google.android.youtube/17.36.4 (Linux; U; Android 12; GB) gzip',
                url
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"yt-dlp download error: {result.stderr}")
                return jsonify({'error': f'YouTube download failed: {result.stderr[:200]}'}), 500
        else:
            return jsonify({'error': 'Unsupported URL'}), 400
            
        return jsonify({'message': 'Download complete'}), 200
    except subprocess.CalledProcessError as e:
        print(f"Error during download: {e}")
        return jsonify({'error': 'Failed to download song'}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)