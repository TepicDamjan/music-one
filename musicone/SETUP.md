# Setup Uputstva

## Backend (Flask Server)

1. Instaliraj Python zavisnosti:
```bash
cd Server
pip install flask flask-cors spotipy
pip install spotdl
```

2. Pokreni Flask server:
```bash
python app.py
```

Server će raditi na `http://localhost:5000`

## Frontend (Next.js)

1. Instaliraj Node.js zavisnosti:
```bash
cd musicone
npm install
```

2. (Opciono) Kreiraj `.env.local` fajl ako želiš da promeniš API URL:
```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

3. Pokreni Next.js development server:
```bash
npm run dev
```

Frontend će raditi na `http://localhost:3000`

## Kako koristiti:

1. Pokreni oba servera (Flask i Next.js)
2. Otvori `http://localhost:3000` u browseru
3. Unesi Spotify URL u input polje
4. Klikni na play dugme
5. Na download stranici će se prikazati informacije o pesmi
6. Klikni na download dugme da preuzmeš pesmu

## Napomena:

- SpotDL će preuzeti pesmu u folderu gde je Flask server pokrenut
- Proveri da li imaš instaliran `spotdl` na sistemu: `pip install spotdl`
