'use client';

import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from "next/link";
import { fetchSongInfo, downloadSong, fetchYoutubeInfo, downloadYoutube, SongInfo, DownloadResult } from '@/app/utils/api';

type AudioFormat = 'mp3' | 'flac' | 'mp4';

const SPOTIFY_FORMATS: AudioFormat[] = ['mp3', 'flac'];
const YOUTUBE_FORMATS: AudioFormat[] = ['mp3', 'flac', 'mp4'];

const FORMAT_LABELS: Record<AudioFormat, { label: string; icon: string; desc: string }> = {
    mp3:  { label: 'MP3',  icon: '🎵', desc: 'Univerzalan, manji fajl' },
    flac: { label: 'FLAC', icon: '🎼', desc: 'Lossless, veći kvalitet' },
    mp4:  { label: 'MP4',  icon: '🎬', desc: 'Video + audio' },
};

/** Heurističke faze dok čekamo sync download (nema pravog % sa servera). */
const DOWNLOAD_PHASES: { atMs: number; progress: number; label: string }[] = [
    { atMs: 0, progress: 8, label: 'Povezivanje sa serverom…' },
    { atMs: 2500, progress: 22, label: 'Pretraga…' },
    { atMs: 8000, progress: 45, label: 'Preuzimanje…' },
    { atMs: 20000, progress: 68, label: 'Konverzija…' },
    { atMs: 45000, progress: 85, label: 'Priprema fajla…' },
];

function ProgressBar({ progress, label }: { progress: number; label: string }) {
    const pct = Math.min(100, Math.max(0, Math.round(progress)));
    return (
        <div className="w-full max-w-sm space-y-2" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div className="flex justify-between items-center text-greenPtext text-xs">
                <span className="opacity-80">{label}</span>
                <span className="font-bold tabular-nums">{pct}%</span>
            </div>
            <div className="h-2.5 w-full rounded-full bg-greenBG border border-greenPtext/30 overflow-hidden">
                <div
                    className="h-full rounded-full bg-greenPtext transition-[width] duration-500 ease-out"
                    style={{ width: `${pct}%` }}
                />
            </div>
        </div>
    );
}

function Download() {
    const searchParams = useSearchParams();
    const [songInfo, setSongInfo] = useState<SongInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [downloading, setDownloading] = useState(false);
    const [error, setError] = useState<string>('');
    const [downloadSuccess, setDownloadSuccess] = useState(false);
    const [savedTo, setSavedTo] = useState<string>('');
    const [loadingMessage, setLoadingMessage] = useState('Učitavanje...');
    const [selectedFormat, setSelectedFormat] = useState<AudioFormat>('mp3');
    const [progress, setProgress] = useState(0);
    const [progressLabel, setProgressLabel] = useState('');
    const phaseTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

    const url = searchParams.get('url');
    const platform = (searchParams.get('platform') || 'spotify') as 'spotify' | 'youtube';
    const availableFormats = platform === 'youtube' ? YOUTUBE_FORMATS : SPOTIFY_FORMATS;

    const clearPhaseTimers = () => {
        phaseTimersRef.current.forEach(clearTimeout);
        phaseTimersRef.current = [];
    };

    const startPhaseTimers = () => {
        clearPhaseTimers();
        DOWNLOAD_PHASES.forEach(({ atMs, progress: p, label }) => {
            const id = setTimeout(() => {
                setProgress((prev) => Math.max(prev, p));
                setProgressLabel(label);
            }, atMs);
            phaseTimersRef.current.push(id);
        });
    };

    useEffect(() => () => clearPhaseTimers(), []);

    useEffect(() => {
        if (!url) {
            setError('URL nije pronađen');
            setLoading(false);
            return;
        }

        const loadInfo = async () => {
            try {
                setLoading(true);
                setError('');
                setLoadingMessage('Povezivanje sa serverom...');
                setTimeout(() => setLoadingMessage('Učitavanje informacija...'), 3000);

                let info: SongInfo;
                if (platform === 'youtube') {
                    info = await fetchYoutubeInfo(url);
                } else {
                    info = await fetchSongInfo(url);
                }

                setSongInfo(info);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Greška pri učitavanju informacija');
            } finally {
                setLoading(false);
                setLoadingMessage('Učitavanje...');
            }
        };

        loadInfo();
    }, [url, platform]);

    const handleDownload = async () => {
        if (!url) return;

        try {
            setDownloading(true);
            setError('');
            setDownloadSuccess(false);
            setSavedTo('');
            setProgress(0);
            setProgressLabel(DOWNLOAD_PHASES[0].label);
            startPhaseTimers();

            let result: DownloadResult;
            if (platform === 'youtube') {
                result = await downloadYoutube(url, selectedFormat);
            } else {
                result = await downloadSong(url, selectedFormat);
            }

            clearPhaseTimers();
            setProgress(100);
            setProgressLabel('Gotovo!');
            setSavedTo(result.filename ? `Preuzeto: ${result.filename}` : result.message);
            setDownloadSuccess(true);
        } catch (err) {
            clearPhaseTimers();
            setProgress(0);
            setProgressLabel('');
            setError(err instanceof Error ? err.message : 'Greška pri preuzimanju');
        } finally {
            setDownloading(false);
        }
    };

    const formatDuration = (ms: number) => {
        if (!ms) return '';
        const minutes = Math.floor(ms / 60000);
        const seconds = Math.floor((ms % 60000) / 1000);
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    const platformBadge = platform === 'youtube'
        ? <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded-full">YouTube</span>
        : <span className="text-xs bg-green-700 text-white px-2 py-0.5 rounded-full">Spotify</span>;

    return (
        <div className="w-full min-h-screen flex justify-center items-center p-4">
            <div className="flex justify-center items-center w-full max-w-md">
                <div className="flex flex-col gap-6 justify-center items-center p-4 md:p-8 w-full">

                    {loading ? (
                        <div className="text-greenPtext text-center space-y-3">
                            <div className="animate-pulse text-lg">{loadingMessage}</div>
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
                            {/* Thumbnail */}
                            <div className="w-48 h-48 md:w-64 md:h-64 rounded-lg overflow-hidden shadow-xl">
                                <img
                                    src={songInfo.album_image}
                                    alt={songInfo.name}
                                    className="w-full h-full object-cover"
                                />
                            </div>

                            {/* Info */}
                            <div className="text-greenPtext text-center space-y-2 px-2">
                                <div className="flex justify-center">{platformBadge}</div>
                                <h2 className="text-xl md:text-2xl font-bold break-words">{songInfo.name}</h2>
                                <p className="text-base md:text-lg">{songInfo.artist}</p>
                                {songInfo.is_playlist && (
                                    <p className="text-sm opacity-70">📂 Playlist</p>
                                )}
                                {songInfo.duration_ms > 0 && !songInfo.is_playlist && (
                                    <p className="text-sm opacity-70">{formatDuration(songInfo.duration_ms)}</p>
                                )}
                            </div>

                            {/* Format selector */}
                            {!downloadSuccess && !downloading && (
                                <div className="w-full">
                                    <p className="text-greenPtext text-xs text-center mb-2 opacity-70 uppercase tracking-wider">Format</p>
                                    <div className="flex flex-row gap-2 justify-center">
                                        {availableFormats.map((fmt) => {
                                            const isSelected = selectedFormat === fmt;
                                            const meta = FORMAT_LABELS[fmt];
                                            return (
                                                <button
                                                    key={fmt}
                                                    onClick={() => setSelectedFormat(fmt)}
                                                    title={meta.desc}
                                                    className={`flex flex-col items-center justify-center w-20 h-16 rounded-xl border-2 transition-all duration-150 text-sm font-bold
                                                        ${isSelected
                                                            ? 'bg-greenPtext text-greenBG border-greenPtext scale-105 shadow-md'
                                                            : 'bg-greenBG text-greenPtext border-greenPtext opacity-50 hover:opacity-80'
                                                        }`}
                                                >
                                                    <span className="text-base">{meta.icon}</span>
                                                    <span>{meta.label}</span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                    <p className="text-greenPtext text-xs text-center mt-1 opacity-50">
                                        {FORMAT_LABELS[selectedFormat].desc}
                                    </p>
                                </div>
                            )}

                            {/* Progress */}
                            {(downloading || (downloadSuccess && progress === 100)) && progressLabel && (
                                <ProgressBar progress={progress} label={progressLabel} />
                            )}

                            {/* Success */}
                            {downloadSuccess && (
                                <div className="text-green-600 text-center font-bold space-y-1">
                                    <div>✅ Preuzimanje završeno! ({selectedFormat.toUpperCase()})</div>
                                    {savedTo && (
                                        <div className="text-xs opacity-70 font-normal break-all">
                                            {savedTo}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Error */}
                            {error && (
                                <div className="text-red-500 text-center text-sm">
                                    {error}
                                </div>
                            )}

                            {/* Buttons */}
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
                                        <div className="text-greenPtext animate-pulse text-xs text-center px-1">
                                            {selectedFormat.toUpperCase()}…
                                        </div>
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
