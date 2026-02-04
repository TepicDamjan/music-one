# MusicOne Server

Backend API server for MusicOne application built with Flask.

## Deployment to Render

### Prerequisites
1. Create a Render account at [render.com](https://render.com)
2. Connect your GitHub repository
3. Create a new Web Service on Render

### Environment Variables
Set these environment variables in your Render dashboard:

```
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
YOUTUBE_API_KEY=your_youtube_api_key (optional)
YOUTUBE_COOKIES=your_youtube_cookies (optional, for age-restricted content)
```

### Render Configuration
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --timeout 600 --workers 1 app:app`
- **Runtime**: Python 3.11
- **Plan**: Free tier works for basic usage

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

### Notes
- The server uses system-installed FFmpeg (handled by Dockerfile)
- YouTube cookies should be provided via environment variables, not files
- Large binary files like `ffmpeg.exe` and `cookies.txt` are excluded via `.gitignore`