const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export interface SongInfo {
  name: string;
  artist: string;
  album: string;
  release_date: string;
  duration_ms: number;
  album_image: string;
}

// Helper function to add timeout to fetch
const fetchWithTimeout = async (url: string, options: RequestInit, timeout: number = 30000): Promise<Response> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Zahtev je prekoračio vreme čekanja. Proverite da li je server pokrenut.');
    }
    throw error;
  }
};

// Helper function to retry failed requests
const fetchWithRetry = async (
  url: string,
  options: RequestInit,
  timeout: number = 60000,
  retries: number = 2
): Promise<Response> => {
  let lastError: Error | null = null;
  
  for (let i = 0; i <= retries; i++) {
    try {
      console.log(`Pokušaj ${i + 1} od ${retries + 1}...`);
      const response = await fetchWithTimeout(url, options, timeout);
      return response;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error('Nepoznata greška');
      console.warn(`Pokušaj ${i + 1} nije uspeo:`, lastError.message);
      
      if (i < retries) {
        const waitTime = (i + 1) * 2000;
        console.log(`Čekanje ${waitTime}ms pre sledećeg pokušaja...`);
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }
  }
  
  throw lastError || new Error('Svi pokušaji su neuspešni');
};

export const fetchSongInfo = async (url: string): Promise<SongInfo> => {
  try {
    console.log('Fetching song info for URL:', url);
    console.log('API Base URL:', API_BASE_URL);
    
    const response = await fetchWithRetry(
      `${API_BASE_URL}/song-info`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      },
      60000,
      2
    );

    if (!response.ok) {
      let errorMessage = 'Neuspešno učitavanje informacija o pesmi';
      try {
        const error = await response.json();
        errorMessage = error.error || errorMessage;
      } catch (e) {
        errorMessage = `Server je vratio grešku: ${response.status} ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    console.log('Song info received:', data);
    return data;
  } catch (error) {
    console.error('Error in fetchSongInfo:', error);
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Ne mogu da se povežem sa serverom. Server možda spava - pokušajte ponovo za nekoliko sekundi.');
    }
    throw error;
  }
};

export const downloadSong = async (url: string): Promise<void> => {
  try {
    console.log('Downloading song for URL:', url);
    
    const response = await fetchWithRetry(
      `${API_BASE_URL}/download`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      },
      300000,
      1
    );

    if (!response.ok) {
      let errorMessage = 'Neuspešno preuzimanje pesme';
      try {
        const error = await response.json();
        errorMessage = error.error || errorMessage;
      } catch (e) {
        errorMessage = `Server je vratio grešku: ${response.status} ${response.statusText}`;
      }
      throw new Error(errorMessage);
    }

    return response.json();
  } catch (error) {
    console.error('Error in downloadSong:', error);
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new Error('Ne mogu da se povežem sa serverom. Proverite da li je server pokrenut na ' + API_BASE_URL);
    }
    throw error;
  }
};
