'use client';

import { useRef, useState } from 'react';
import Navbar from "@/app/components/Navbar";
import { useRouter } from "next/navigation";

function Home() {
    const inputRef = useRef<HTMLInputElement>(null);
    const router = useRouter();
    const [error, setError] = useState<string>('');

    const handlePaste = async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (inputRef.current) {
                inputRef.current.value = text;
            }
        } catch (err) {
            console.error('Failed to read from clipboard: ', err);
        }
    };

    const handlePlay = () => {
        const url = inputRef.current?.value.trim();
        if (!url) {
            setError('Molimo unesite URL');
            return;
        }

        // Validacija URL-a za Spotify ili YouTube
        const isSpotify = url.includes('open.spotify.com') || url.includes('spotify.com');
        const isYouTube = url.includes('youtube.com') || url.includes('youtu.be');
        
        if (!isSpotify && !isYouTube) {
            setError('Molimo unesite validan Spotify ili YouTube URL');
            return;
        }

        setError('');
        router.push(`/download?url=${encodeURIComponent(url)}`);
    };

    return (
        <>

            <div className="min-h-screen flex flex-col gap-20 md:gap-40 justify-center items-center w-full px-4">
                <Navbar/>
                <div className="w-full max-w-3xl flex flex-col items-center justify-center">
                    <div
                        className="p-4 flex flex-col md:flex-row gap-4 md:gap-9 w-full max-w-2xl h-auto md:h-20 rounded-2xl bg-greenPtext items-center justify-center">
                        <input 
                            ref={inputRef}
                            type="text"
                            placeholder="Unesite Spotify ili YouTube URL..."
                            className=" bg-greenBG w-full md:w-3xl h-14 md:h-16 rounded-lg text-greenPtext font-bold p-4 text-sm md:text-base"/>
                        <div className="flex flex-row gap-4 w-full md:w-auto justify-center">
                            <button onClick={handlePaste}
                                    className="w-16 md:w-24 h-14 md:h-16 bg-greenBG rounded-lg flex justify-center items-center cursor-pointer hover:opacity-80 transition-opacity">

                                <svg width="30" height="30" viewBox="0 0 40 40" fill="none"
                                     xmlns="http://www.w3.org/2000/svg" className="md:w-[40px] md:h-[40px]">
                                    <path
                                        d="M10.9993 18.9957C10.9993 14.452 10.9993 12.1802 12.4052 10.7687C13.8111 9.35712 16.0738 9.35712 20.5993 9.35712H25.3993C29.9248 9.35712 32.1875 9.35712 33.5935 10.7687C34.9993 12.1802 34.9993 14.452 34.9993 18.9957V27.0278C34.9993 31.5715 34.9993 33.8433 33.5935 35.2549C32.1875 36.6664 29.9248 36.6663 25.3993 36.6663H20.5993C16.0738 36.6663 13.8111 36.6664 12.4052 35.2549C10.9993 33.8433 10.9993 31.5715 10.9993 27.0278V18.9957Z"
                                        fill="#35524A"/>
                                    <path opacity="0.5"
                                          d="M6.95262 5.28596C5 7.23859 5 10.3813 5 16.6667V20C5 26.2853 5 29.4282 6.95262 31.3807C7.98188 32.41 9.34183 32.8967 11.3184 33.1268C10.9993 31.7255 10.9993 29.7993 10.9993 27.0278V18.9957C10.9993 14.452 10.9993 12.1802 12.4052 10.7686C13.8111 9.35711 16.0739 9.35711 20.5993 9.35711H25.3993C28.1525 9.35711 30.0682 9.35711 31.4628 9.67491C31.2338 7.68578 30.7473 6.31924 29.714 5.28596C27.7615 3.33334 24.6187 3.33334 18.3333 3.33334C12.0479 3.33334 8.90525 3.33334 6.95262 5.28596Z"
                                          fill="#35524A"/>
                                </svg>

                            </button>
                            <button 
                                type="button"
                                onClick={handlePlay}
                                className="w-16 md:w-24 h-14 md:h-16 bg-greenBG rounded-lg flex justify-center items-center cursor-pointer hover:opacity-80 transition-opacity relative z-10">
                                <svg width="30" height="30" viewBox="0 0 39 41" fill="none"
                                     xmlns="http://www.w3.org/2000/svg"
                                     className="pointer-events-none md:w-[39px] md:h-[41px]">
                                    <path
                                        d="M5 12.2592V28.2092C5 31.4759 8.55 33.5259 11.3833 31.8926L18.3 27.9092L25.2166 23.9092C28.05 22.2759 28.05 18.1926 25.2166 16.5592L18.3 12.5592L11.3833 8.57585C8.55 6.94251 5 8.97585 5 12.2592Z"
                                        fill="#35524A"/>
                                    <path
                                        d="M32.5917 31.7831C31.9083 31.7831 31.3417 31.2164 31.3417 30.5331V9.93311C31.3417 9.24977 31.9083 8.68311 32.5917 8.68311C33.275 8.68311 33.8417 9.24977 33.8417 9.93311V30.5331C33.8417 31.2164 33.2917 31.7831 32.5917 31.7831Z"
                                        fill="#35524A"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    {error && (
                        <div className="mt-4 text-red-500 text-center">
                            {error}
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}

export default Home;