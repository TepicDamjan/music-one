'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from "next/link";
import { fetchSongInfo, downloadSong, SongInfo } from '@/app/utils/api';

function Download() {
    const searchParams = useSearchParams();
    const [songInfo, setSongInfo] = useState<SongInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [downloading, setDownloading] = useState(false);
    const [error, setError] = useState<string>('');
    const [downloadSuccess, setDownloadSuccess] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState('Učitavanje...');

    const url = searchParams.get('url');

    useEffect(() => {
        if (!url) {
            setError('URL nije pronađen');
            setLoading(false);
            return;
        }

        const loadSongInfo = async () => {
            try {
                setLoading(true);
                setError('');
                setLoadingMessage('Povezivanje sa serverom...');
                console.log('Loading song info for URL:', url);
                
                setTimeout(() => {
                    if (loading) {
                        setLoadingMessage('Server se budi, molimo sačekajte...');
                    }
                }, 5000);
                
                setTimeout(() => {
                    if (loading) {
                        setLoadingMessage('Još malo, skoro gotovo...');
                    }
                }, 15000);
                
                const info = await fetchSongInfo(url);
                console.log('Song info loaded successfully:', info);
                setSongInfo(info);
            } catch (err) {
                const errorMessage = err instanceof Error ? err.message : 'Greška pri učitavanju informacija o pesmi';
                console.error('Error fetching song info:', err);
                setError(errorMessage);
            } finally {
                setLoading(false);
                setLoadingMessage('Učitavanje...');
            }
        };

        loadSongInfo();
    }, [url]);

    const handleDownload = async () => {
        if (!url) return;

        try {
            setDownloading(true);
            setError('');
            setDownloadSuccess(false);
            await downloadSong(url);
            setDownloadSuccess(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Greška pri preuzimanju pesme');
            console.error('Error downloading song:', err);
        } finally {
            setDownloading(false);
        }
    };

    const formatDuration = (ms: number) => {
        const minutes = Math.floor(ms / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    return (
        <div className="w-full min-h-screen flex justify-center items-center p-4">
            <div className="flex justify-center items-center w-full max-w-md">
                <div className="flex flex-col gap-6 justify-center items-center p-4 md:p-8 w-full">
                    {loading ? (
                        <div className="text-greenPtext text-center space-y-3">
                            <div className="animate-pulse text-lg">{loadingMessage}</div>
                            <div className="text-sm opacity-70">
                                {loadingMessage.includes('budi') && '(Besplatni server spava posle neaktivnosti)'}
                            </div>
                        </div>
                    ) : error && !songInfo ? (
                        <div className="text-red-500 text-center">
                            <p className="mb-4">{error}</p>
                            <Link href="/" className="text-greenPtext underline">
                                Vrati se na početnu
                            </Link>
                        </div>
                    ) : songInfo ? (
                        <>
                            <div className="w-48 h-48 md:w-64 md:h-64 rounded-lg overflow-hidden shadow-xl">
                                <img
                                    src={songInfo.album_image}
                                    alt={songInfo.album}
                                    className="w-full h-full object-cover"
                                />
                            </div>
                            <div className="text-greenPtext text-center space-y-2 px-2">
                                <h2 className="text-xl md:text-2xl font-bold break-words">{songInfo.name}</h2>
                                <p className="text-base md:text-lg">{songInfo.artist}</p>
                                <p className="text-sm md:text-md opacity-80">{songInfo.album}</p>
                            </div>

                            {downloadSuccess && (
                                <div className="text-green-600 text-center font-bold">
                                    Preuzimanje završeno!
                                </div>
                            )}

                            {error && (
                                <div className="text-red-500 text-center">
                                    {error}
                                </div>
                            )}

                            <div className='flex flex-row justify-center items-center gap-4'>
                                <Link
                                    href="/"
                                    className="w-24 h-16 bg-greenBG rounded-lg flex justify-center items-center cursor-pointer hover:opacity-80 transition-opacity relative z-10 border-2 border-greenPtext">
                                    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path fillRule="evenodd" clipRule="evenodd" d="M19.6667 3C10.4619 3 3 10.4619 3 19.6667C3 28.8713 10.4619 36.3333 19.6667 36.3333C28.8713 36.3333 36.3333 28.8713 36.3333 19.6667C36.3333 10.4619 28.8713 3 19.6667 3ZM6.33333 19.6667C6.33333 12.3029 12.3029 6.33333 19.6667 6.33333C27.0305 6.33333 33 12.3029 33 19.6667C33 27.0305 27.0305 33 19.6667 33C12.3029 33 6.33333 27.0305 6.33333 19.6667Z" fill="#35524A"/>
                                        <path d="M15.9088 13.5911C15.2688 12.9511 14.2311 12.9511 13.5911 13.5911C12.9511 14.2311 12.9511 15.2688 13.5911 15.9088L17.3489 19.6666L13.5911 23.4244C12.9511 24.0644 12.9511 25.1022 13.5911 25.7422C14.2311 26.3822 15.2688 26.3822 15.9088 25.7422L19.6666 21.9844L23.4244 25.7422C24.0644 26.3822 25.1022 26.3822 25.7422 25.7422C26.3822 25.1022 26.3822 24.0644 25.7422 23.4244L21.9844 19.6666L25.7422 15.9088C26.3822 15.2688 26.3822 14.2311 25.7422 13.5911C25.1022 12.9511 24.0644 12.9511 23.4244 13.5911L19.6666 17.3489L15.9088 13.5911Z" fill="#35524A"/>
                                    </svg>
                                </Link>
                                <button
                                    onClick={handleDownload}
                                    disabled={downloading || downloadSuccess}
                                    className="w-24 h-16 bg-greenBG rounded-lg flex justify-center items-center cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed border-2 border-greenPtext">
                                    {downloading ? (
                                        <div className="text-greenPtext">...</div>
                                    ) : (
                                        <svg width="40" height="42" viewBox="0 0 40 42" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M19.9999 5V26.6667M19.9999 26.6667L26.6666 19.375M19.9999 26.6667L13.3333 19.375" stroke="#35524A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                            <path d="M25 36.6667H15C10.2859 36.6667 7.92893 36.6667 6.46447 35.2022C5 33.7377 5 31.3807 5 26.6667M35 26.6667C35 31.3807 35 33.7377 33.5355 35.2022C33.0358 35.7019 32.4323 36.031 31.6667 36.2479" stroke="#35524A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                        </svg>
                                    )}
                                </button>
                            </div>
                        </>
                    ) : null}
                </div>
            </div>
        </div>
    );
}

export default Download;