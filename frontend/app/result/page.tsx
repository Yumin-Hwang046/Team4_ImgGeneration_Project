'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import NavBar from '@/app/components/NavBar';
import type { GenerateImageResponse } from '@/lib/api';

const STORAGE_KEY = 'generatorResult';

type StoredResult = GenerateImageResponse & {
  mood: string;
  size: string;
  userPrompt: string;
};

function toDataUrl(b64: string) {
  return `data:image/jpeg;base64,${b64}`;
}

function downloadImage(b64: string, filename: string) {
  const a = document.createElement('a');
  a.href = toDataUrl(b64);
  a.download = filename;
  a.click();
}

function EmptyState() {
  const router = useRouter();
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6">
      <p className="text-xl font-headline font-bold text-on-surface">결과가 없습니다</p>
      <p className="text-on-surface-variant">이미지를 먼저 생성해주세요.</p>
      <button
        onClick={() => router.push('/generator')}
        className="px-8 py-3 bg-primary text-on-primary rounded-xl font-headline font-bold hover:opacity-90 transition-all"
      >
        생성 페이지로 이동
      </button>
    </div>
  );
}

const SIZE_ASPECT: Record<string, string> = {
  square:    'aspect-square',
  portrait:  'aspect-[4/7]',
  landscape: 'aspect-[7/4]',
  naver:     'aspect-[43/60]',
}

function MainImagePanel({
  imageB64,
  size,
  onDownload,
}: {
  imageB64: string;
  size: string;
  onDownload: () => void;
}) {
  const aspectClass = SIZE_ASPECT[size] ?? ''

  return (
    <section className="w-full md:w-[60%] p-8 lg:p-12 flex flex-col items-center justify-center gap-10">
      <div className="w-full max-w-3xl flex justify-center">
        <div className={`bg-surface-container-lowest p-3 rounded-xl shadow-sm border border-outline-variant/20 ${aspectClass ? 'w-fit' : 'w-full'}`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={toDataUrl(imageB64)}
            alt="생성된 마케팅 이미지"
            className={`rounded-lg object-contain max-h-[72vh] w-auto max-w-full ${aspectClass}`}
          />
        </div>
      </div>
      <button
        onClick={onDownload}
        className="flex items-center justify-center gap-2 px-10 py-4 bg-primary-container text-on-primary-container rounded-xl font-headline font-bold text-lg hover:brightness-105 transition-all shadow-md active:scale-95"
      >
        고화질 다운로드
      </button>
    </section>
  );
}

function SettingsSummary({ mood, adCopy }: { mood: string; adCopy: string }) {
  return (
    <div className="bg-surface-container-lowest p-8 rounded-xl shadow-sm flex flex-col gap-6">
      <h2 className="font-headline font-bold text-xl text-on-surface">설정 요약</h2>
      <div className="space-y-4">
        <div>
          <span className="text-xs font-bold text-primary tracking-wider font-headline block mb-1">
            무드
          </span>
          <p className="text-on-surface font-medium">{mood}</p>
        </div>
        <div>
          <span className="text-xs font-bold text-primary tracking-wider font-headline block mb-1">
            광고 문구
          </span>
          <p className="text-on-surface-variant leading-relaxed text-sm">{adCopy}</p>
        </div>
      </div>
    </div>
  );
}

function VariationsGrid({
  results,
}: {
  results: Array<{ ad_copy: string; image_b64: string }>;
}) {
  const variations = results.slice(1, 4);
  if (variations.length === 0) return null;

  return (
    <div className="flex flex-col gap-4">
      <h3 className="font-headline font-bold text-lg text-on-surface">다른 버전</h3>
      <div className="grid grid-cols-3 gap-3">
        {variations.map((item, idx) => (
          <div
            key={idx}
            className="group relative cursor-pointer overflow-hidden rounded-xl bg-surface-container-highest aspect-square border border-transparent hover:border-primary transition-all"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={toDataUrl(item.image_b64)}
              alt={`버전 ${idx + 2}`}
              className="w-full h-full object-cover transition-transform group-hover:scale-110"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function HashtagChips({ hashtags }: { hashtags: string[] }) {
  if (hashtags.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {hashtags.map((tag) => (
        <span
          key={tag}
          className="px-3 py-1.5 bg-secondary-container text-on-secondary-container text-xs font-bold rounded-full"
        >
          {tag.startsWith('#') ? tag : `#${tag}`}
        </span>
      ))}
    </div>
  );
}

function ResultPanel({
  result,
  onRegenerate,
}: {
  result: StoredResult;
  onRegenerate: () => void;
}) {
  const mainResult = result.results[0];

  return (
    <aside className="w-full md:w-[40%] bg-surface-container-low p-8 lg:p-12 flex flex-col gap-8 overflow-y-auto">
      <div className="tracking-[0.1em] text-[0.65rem] uppercase font-bold text-on-surface-variant/60 font-headline">
        Creation Summary • 결과 리포트
      </div>
      <SettingsSummary mood={result.mood} adCopy={mainResult?.ad_copy ?? ''} />
      <VariationsGrid results={result.results} />
      {result.product_description && (
        <div>
          <h3 className="font-headline font-bold text-base text-on-surface mb-2">상품 설명</h3>
          <p className="text-sm text-on-surface-variant leading-relaxed">
            {result.product_description}
          </p>
        </div>
      )}
      <HashtagChips hashtags={result.hashtags} />
      <div className="mt-auto">
        <button
          onClick={onRegenerate}
          className="w-full py-4 border-2 border-outline-variant/30 rounded-xl font-headline font-bold text-on-surface hover:bg-surface-container-high transition-all flex items-center justify-center gap-2"
        >
          다시 생성하기
        </button>
        <p className="text-[0.7rem] text-center text-on-secondary-container mt-4 opacity-70">
          이미지가 마음에 들지 않나요? 설정을 변경하여 다시 시도해 보세요.
        </p>
      </div>
    </aside>
  );
}

export default function ResultPage() {
  const router = useRouter();
  const [result, setResult] = useState<StoredResult | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        setResult(JSON.parse(raw) as StoredResult);
      }
    } catch {
      // ignore parse errors
    } finally {
      setLoaded(true);
    }
  }, []);

  const handleDownload = useCallback(() => {
    if (!result?.results[0]) return;
    downloadImage(result.results[0].image_b64, 'nordic-muse-result.jpg');
  }, [result]);

  const handleRegenerate = useCallback(() => {
    router.push('/generator');
  }, [router]);

  if (!loaded) {
    return (
      <div className="min-h-screen flex flex-col font-body">
        <NavBar />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-on-surface-variant">불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (!result || !result.results?.[0]) {
    return (
      <div className="min-h-screen flex flex-col font-body">
        <NavBar />
        <EmptyState />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col font-body">
      <NavBar />
      <main className="flex flex-col md:flex-row flex-1 overflow-hidden">
        <MainImagePanel
          imageB64={result.results[0].image_b64}
          size={result.size}
          onDownload={handleDownload}
        />
        <ResultPanel result={result} onRegenerate={handleRegenerate} />
      </main>
    </div>
  );
}
