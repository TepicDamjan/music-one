from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import sys
import json
import shutil
import time
import mimetypes
import zipfile
import tempfile

MEDIA_EXTENSIONS = {'.mp3', '.flac', '.mp4', '.m4a', '.webm', '.opus', '.ogg', '.wav', '.mkv'}

app = Flask(__name__)
CORS(app, expose_headers=['Content-Disposition'])

# Spotify API kljucevi
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')


def _resolve_download_dir():
    """Env DOWNLOAD_DIR ako je set; inace /app/downloads u Dockeru ako postoji; inace ~/Music/MusicOne."""
    raw = os.environ.get('DOWNLOAD_DIR', '').strip()
    if raw:
        return os.path.abspath(raw)
    docker_default = '/app/downloads'
    if os.path.isdir(docker_default) and os.access(docker_default, os.W_OK):
        return docker_default
    return os.path.abspath(os.path.expanduser('~/Music/MusicOne'))


# Direktorijum za preuzimanje (lokalno: ~/Music/MusicOne; Docker image: /app/downloads)
DOWNLOAD_DIR = _resolve_download_dir()
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
print(f"Downloads will be saved to: {DOWNLOAD_DIR}")

# Opcioni proxy samo za spotdl / yt-dlp (npr. residential proxy da Oracle IP ne bude blokiran).
# Postavi MUSICONE_PROXY, npr. http://user:pass@host:port ili socks5://host:1080
MUSICONE_PROXY = os.environ.get('MUSICONE_PROXY', '').strip()
if MUSICONE_PROXY:
    print('MUSICONE_PROXY is set; spotdl and yt-dlp will use it for outbound requests.')

def _download_proxy_cmd():
    """Vraca ['--proxy', url] ako je MUSICONE_PROXY postavljen, inace []."""
    if not MUSICONE_PROXY:
        return []
    return ['--proxy', MUSICONE_PROXY]


_spotdl_major_cache = None


def _get_spotdl_major_version():
    """Keširana major verzija spotdl (4 = download podkomanda)."""
    global _spotdl_major_cache
    if _spotdl_major_cache is not None:
        return _spotdl_major_cache
    version_text = 'unknown'
    try:
        r = subprocess.run(
            [sys.executable, '-m', 'spotdl', '--version'],
            capture_output=True,
            text=True,
            timeout=15,
        )
        version_text = (r.stdout or r.stderr or '').strip()
        _spotdl_major_cache = int(version_text.split('.')[0]) if version_text else 4
    except Exception:
        _spotdl_major_cache = 4
    print(f'spotdl version: {version_text} (major={_spotdl_major_cache})')
    return _spotdl_major_cache


def _spotdl_argv(url: str, fmt: str):
    """spotdl 4.x: 'python -m spotdl download ...'. v3: bez download podkomande."""
    base = [sys.executable, '-m', 'spotdl']
    if _get_spotdl_major_version() >= 4:
        cmd = base + ['download']
    else:
        cmd = base
    cmd.extend([
        '--format', fmt,
        '--output', DOWNLOAD_DIR,
        '--audio', 'youtube-music',
        '--overwrite', 'force',
    ])
    if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
        cmd.extend(['--client-id', SPOTIFY_CLIENT_ID, '--client-secret', SPOTIFY_CLIENT_SECRET])
    # Ne koristiti --yt-dlp-args ovde: pogresan format lomi spotdl CLI (usage:).
    # Node je u Docker image-u; spotdl/yt-dlp ga nasledi iz PATH.
    cmd.extend(_download_proxy_cmd())
    cmd.append(url)
    return cmd


def _yt_dlp_argv():
    """Osnova yt-dlp komande: proxy + JS runtime (YouTube cesto zahteva Node/deno)."""
    out = ['yt-dlp', *_download_proxy_cmd()]
    js = os.environ.get('YTDLP_JS_RUNTIMES', '').strip()
    if js:
        out.extend(['--js-runtimes', js])
        return out
    node = shutil.which('node') or shutil.which('nodejs')
    if node:
        out.extend(['--js-runtimes', f'node:{node}'])
        return out
    deno = shutil.which('deno')
    if deno:
        out.extend(['--js-runtimes', f'deno:{deno}'])
    return out


def _snapshot_download_dir():
    """Relativna putanja (od DOWNLOAD_DIR) -> mtime pre preuzimanja."""
    snap = {}
    if not os.path.isdir(DOWNLOAD_DIR):
        return snap
    for dirpath, _, filenames in os.walk(DOWNLOAD_DIR):
        for name in filenames:
            if name.startswith('.'):
                continue
            path = os.path.join(dirpath, name)
            if not os.path.isfile(path):
                continue
            try:
                rel = os.path.relpath(path, DOWNLOAD_DIR)
                snap[rel] = os.path.getmtime(path)
            except (OSError, ValueError):
                continue
    return snap


def _collect_paths_after_download(snapshot_before):
    """Medija fajlovi koji su novi ili imaju noviji mtime (posle spotdl/yt-dlp)."""
    paths = []
    if not os.path.isdir(DOWNLOAD_DIR):
        return paths
    for dirpath, _, filenames in os.walk(DOWNLOAD_DIR):
        for name in filenames:
            if name.startswith('.'):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in MEDIA_EXTENSIONS:
                continue
            path = os.path.join(dirpath, name)
            if not os.path.isfile(path):
                continue
            try:
                rel = os.path.relpath(path, DOWNLOAD_DIR)
                mt = os.path.getmtime(path)
            except (OSError, ValueError):
                continue
            prev = snapshot_before.get(rel)
            if prev is None or mt > prev + 0.25:
                paths.append((path, mt))
    paths.sort(key=lambda x: -x[1])
    return [p for p, _ in paths]


def _download_dir_real():
    try:
        return os.path.realpath(DOWNLOAD_DIR)
    except OSError:
        return os.path.abspath(DOWNLOAD_DIR)


def _is_safe_media_path(path: str) -> bool:
    """Fajl mora biti ispod DOWNLOAD_DIR i imati poznatu medija ekstenziju."""
    if not path or not os.path.isfile(path):
        return False
    try:
        root = _download_dir_real()
        p = os.path.realpath(path)
        ext = os.path.splitext(p)[1].lower()
        if ext not in MEDIA_EXTENSIONS:
            return False
        return p == root or p.startswith(root + os.sep)
    except (OSError, ValueError):
        return False


def _paths_from_ytdlp_logs(stdout: str, stderr: str):
    """Parsira apsolutne putanje koje yt-dlp ispisuje (--print after_move ili sl.)."""
    ordered = []
    seen = set()
    for block in (stdout or '', stderr or ''):
        for raw in block.splitlines():
            line = raw.strip().strip('\ufeff').strip('"').strip("'")
            if not line or line.startswith('{'):
                continue
            if line.startswith(('[download]', 'WARNING:', 'ERROR:', 'Deprecated:')):
                continue
            if not os.path.isabs(line):
                continue
            if not _is_safe_media_path(line):
                continue
            rp = os.path.realpath(line)
            if rp not in seen:
                seen.add(rp)
                ordered.append(rp)
    return ordered


def _collect_paths_since_start(started_at: float, slack_sec=5.0):
    """Poslednji fallback: medija fajlovi u DOWNLOAD_DIR sa mtime >= started_at - slack."""
    cutoff = started_at - slack_sec
    found = []
    if not os.path.isdir(DOWNLOAD_DIR):
        return found
    for dirpath, _, filenames in os.walk(DOWNLOAD_DIR):
        for name in filenames:
            if name.startswith('.') or name.endswith('.part'):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in MEDIA_EXTENSIONS:
                continue
            path = os.path.join(dirpath, name)
            if not os.path.isfile(path):
                continue
            try:
                mt = os.path.getmtime(path)
            except OSError:
                continue
            if mt >= cutoff:
                found.append((path, mt))
    found.sort(key=lambda x: -x[1])
    return [p for p, _ in found]


def _response_with_downloaded_files(snapshot_before, preferred_paths=None, started_at=None):
    """Vraca send_file (jedan fajl ili zip) ili JSON gresku ako nema fajlova."""
    paths = []
    if preferred_paths:
        paths = [p for p in preferred_paths if _is_safe_media_path(p)]
    if not paths:
        paths = _collect_paths_after_download(snapshot_before)
    if not paths and started_at is not None:
        paths = _collect_paths_since_start(started_at)
    if not paths:
        try:
            names = os.listdir(DOWNLOAD_DIR)
        except OSError:
            names = []
        print(
            f"No new media files under {DOWNLOAD_DIR} (had {len(snapshot_before)} paths in snapshot; "
            f"now {len(names)} top-level names: {names[:20]})"
        )
        return jsonify({'error': 'Preuzimanje je završeno, ali odgovarajući fajl nije pronađen u download folderu.'}), 500

    if len(paths) == 1:
        path = paths[0]
        mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        return send_file(
            path,
            as_attachment=True,
            download_name=os.path.basename(path),
            mimetype=mime,
            max_age=0,
        )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.zip', dir=DOWNLOAD_DIR)
    tmp_path = tmp.name
    tmp.close()
    try:
        with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for p in paths:
                zf.write(p, arcname=os.path.basename(p))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    @after_this_request
    def _cleanup_zip(response):
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return response

    return send_file(
        tmp_path,
        as_attachment=True,
        download_name='musicone-download.zip',
        mimetype='application/zip',
        max_age=0,
    )

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
        snapshot_before = _snapshot_download_dir()
        started_at = time.time()

        cmd = _spotdl_argv(url, fmt)
        print(f"spotdl cmd: {' '.join(cmd[:8])}...")

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=400, cwd=DOWNLOAD_DIR
        )

        if result.returncode != 0:
            print(f"spotdl stdout: {result.stdout[-800:] if result.stdout else ''}")
            print(f"spotdl stderr: {result.stderr[-800:] if result.stderr else ''}")
            err = (result.stderr or result.stdout or 'Nepoznata greška spotdl').strip()
            if err.startswith('usage:') or 'usage: spotdl' in err:
                err = 'spotdl je pozvan sa pogrešnim argumentima. Proveri docker logs.'
            elif len(err) > 280:
                err = err[:280] + '...'
            return jsonify({'error': f'Spotify download failed: {err}'}), 500

        return _response_with_downloaded_files(
            snapshot_before, preferred_paths=None, started_at=started_at
        )

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
            *_yt_dlp_argv(),
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
        snapshot_before = _snapshot_download_dir()
        started_at = time.time()

        output_template = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
        tail = [
            '--no-progress',
            '--print', 'after_move:%(filepath)s',
            '-o', output_template,
            url,
        ]

        if fmt == 'mp4':
            # Video + audio, spoji u MP4
            cmd = [
                *_yt_dlp_argv(),
                '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                '--merge-output-format', 'mp4',
                '--add-metadata',
                '--embed-thumbnail',
                *tail,
            ]
        else:
            # Audio only: mp3 ili flac
            cmd = [
                *_yt_dlp_argv(),
                '-x',
                '--audio-format', fmt,
                '--audio-quality', '0',      # Najbolji kvalitet
                '--add-metadata',
                '--embed-thumbnail',
                *tail,
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            print(f"yt-dlp error: {result.stderr}")
            return jsonify({'error': f'YouTube download failed: {result.stderr[:200]}'}), 500

        preferred = _paths_from_ytdlp_logs(result.stdout, result.stderr)
        if not preferred:
            print(
                'yt-dlp finished OK but no filepath in logs; stdout tail:',
                (result.stdout or '')[-500:],
                'stderr tail:',
                (result.stderr or '')[-500:],
            )
        return _response_with_downloaded_files(
            snapshot_before,
            preferred_paths=(preferred if preferred else None),
            started_at=started_at,
        )

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Download timed out'}), 504
    except Exception as e:
        print(f"Error during YouTube download: {e}")
        return jsonify({'error': 'Failed to download from YouTube'}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
