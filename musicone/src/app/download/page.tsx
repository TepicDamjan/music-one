import { Suspense } from 'react';
import DownloadClient from './DownloadClient';

export default function DownloadPage() {
    return (
        <Suspense fallback={<div className="w-full min-h-screen flex justify-center items-center text-greenPtext">
            Učitavanje...
        </div>}>
            <DownloadClient />
        </Suspense>
    );
}