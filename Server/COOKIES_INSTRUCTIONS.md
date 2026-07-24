# YouTube cookies (rjesenje za 403 / "Sign in to confirm you're not a bot")

YouTube cesto blokira skidanje sa server IP-a ili proxyja. Cookies iz ulogovanog
browsera rijesavaju i bot check i vecinu 403 grešaka na streamu.

## 1. Izvezi cookies na svom PC-u

Najlakse (Chrome, dok si ulogovan na YouTube):

```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt "https://www.youtube.com"
```

Ili Firefox: zamijeni `chrome` sa `firefox`.

Fajl mora biti Netscape format (yt-dlp ga sam napravi). **Nikad ga ne komituj u git.**

## 2. Prebaci na Oracle server

```bash
# sa PC-a (primjer):
scp cookies.txt ubuntu@TVOJ_SERVER_IP:~/cookies.txt
```

## 3. Pokreni kontejner sa mountom cookies fajla

```bash
docker rm -f musicone
docker run -d --name musicone --restart unless-stopped \
  -p 5000:5000 \
  --env-file ~/musicone.env \
  -v ~/downloads:/app/downloads \
  -v ~/cookies.txt:/app/cookies.txt:ro \
  musicone
```

Pri startu u logu treba da pise:

```
YouTube cookies loaded from: /app/cookies.txt
```

## 4. Test unutar kontejnera

```bash
docker exec -it musicone bash
yt-dlp --proxy "$MUSICONE_PROXY" --cookies /app/cookies.txt -x \
  -o '/tmp/test.%(ext)s' 'https://www.youtube.com/watch?v=flulcZNAP5E'
```

Ako i dalje bude 403, cookies su istekli ili proxy IP i dalje blokiran za CDN —
osvjezi cookies (ponovo izvezi sa PC-a) ili probaj drugi proxy endpoint.

## Napomena

Cookies isticeu (obično nakon nekoliko dana/sedmica). Kad opet krene 403 / bot
check, ponovo izvezi i zamijeni `~/cookies.txt`, pa restartuj kontejner (bez rebuilda).
