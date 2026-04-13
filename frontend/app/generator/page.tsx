'use client';

import { useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import NavBar from '@/app/components/NavBar';
import SideBar from '@/app/components/SideBar';
import { generateImage } from '@/lib/api';
import type { GenerateImageResponse } from '@/lib/api';

// Constants
const SIZE_OPTIONS = [
  { value: 'square', label: '인스타 피드', desc: '1200x1200' },
  { value: 'portrait', label: '인스타 스토리', desc: '1080x1350' },
  { value: 'landscape', label: '웹 배너', desc: '720x300' },
] as const;

const MOOD_OPTIONS = [
  { value: '따뜻한 매장 분위기', bg: 'bg-amber-700' },
  { value: '깔끔한 상품 홍보', bg: 'bg-primary' },
  { value: '트렌디한 메뉴 홍보', bg: 'bg-rose-700' },
  { value: '프리미엄 매장·상품', bg: 'bg-neutral-800' },
] as const;

const KEYWORD_CHIPS = ['#먹음직스러운', '#감성적인', '#자연광', '#미니멀'] as const;

type SizeValue = (typeof SIZE_OPTIONS)[number]['value'];
type MoodValue = (typeof MOOD_OPTIONS)[number]['value'];

// Sub-components
function StepLabel({ num, title, sub }: { num: number; title: string; sub?: string }) {
  return (
    <div className="flex items-center gap-4 mb-8">
      <span className="w-8 h-8 rounded-full bg-primary text-on-primary flex items-center justify-center font-headline text-sm font-bold shrink-0">
        {num}
      </span>
      <h2 className="font-headline text-2xl font-bold text-on-surface">{title}</h2>
      {sub && <span className="text-sm text-outline font-medium">{sub}</span>}
    </div>
  );
}

function SizeStep({
  selected,
  onChange,
}: {
  selected: SizeValue;
  onChange: (v: SizeValue) => void;
}) {
  return (
    <section>
      <StepLabel num={1} title="용도 선택" />
      <div className="grid grid-cols-3 gap-6">
        {SIZE_OPTIONS.map((opt) => {
          const isSelected = selected === opt.value;
          return (
            <button
              key={opt.value}
              onClick={() => onChange(opt.value)}
              className={`flex flex-col items-center p-6 bg-surface-container-lowest rounded-2xl border-2 transition-all shadow-sm ${
                isSelected
                  ? 'border-primary ring-8 ring-primary-fixed-dim/10'
                  : 'border-transparent hover:bg-surface-container-low'
              }`}
            >
              <div className="w-16 h-16 bg-surface-container-low rounded-xl flex items-center justify-center mb-4">
                {opt.value === 'square' && (
                  <div className="w-8 h-8 border-2 border-primary/40 rounded-sm" />
                )}
                {opt.value === 'portrait' && (
                  <div className="w-7 h-10 border-2 border-outline-variant/40 rounded-sm" />
                )}
                {opt.value === 'landscape' && (
                  <div className="w-12 h-7 border-2 border-outline-variant/40 rounded-sm" />
                )}
              </div>
              <span className="font-body text-base font-bold text-on-surface">{opt.label}</span>
              <span className="text-xs text-outline mt-2 font-medium">{opt.desc}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function MoodStep({
  selected,
  onChange,
}: {
  selected: MoodValue;
  onChange: (v: MoodValue) => void;
}) {
  return (
    <section>
      <StepLabel num={2} title="무드 선택" />
      <div className="grid grid-cols-2 gap-6 mb-8">
        {MOOD_OPTIONS.map((mood) => {
          const isSelected = selected === mood.value;
          return (
            <div
              key={mood.value}
              onClick={() => onChange(mood.value)}
              className={`relative cursor-pointer overflow-hidden rounded-2xl aspect-[4/3] ${mood.bg} ${
                isSelected ? 'ring-4 ring-primary ring-offset-4 ring-offset-surface' : ''
              }`}
            >
              <div className="absolute inset-0 flex items-end p-5">
                <span className="text-white font-bold text-base font-body">{mood.value}</span>
              </div>
              {isSelected && (
                <div className="absolute top-4 right-4 bg-white rounded-full w-6 h-6 flex items-center justify-center shadow-xl">
                  <span className="text-primary text-xs font-bold">✓</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RefImageStep({
  refImage,
  onFileSelect,
  onClear,
}: {
  refImage: File | null;
  onFileSelect: (f: File) => void;
  onClear: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <section>
      <StepLabel num={3} title="스타일 레퍼런스 선택" />
      <div className="flex gap-3 mb-4">
        <button
          onClick={onClear}
          className="px-6 py-3 bg-surface-container-high rounded-full text-sm font-bold text-on-surface active:scale-95 transition-all"
        >
          레퍼런스 없이 생성
        </button>
        <button
          onClick={() => inputRef.current?.click()}
          className="px-6 py-3 bg-secondary-container text-on-secondary-container rounded-full text-sm font-bold flex items-center gap-2 active:scale-95 transition-all shadow-sm"
        >
          직접 추가
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFileSelect(file);
          }}
        />
      </div>
      {refImage && (
        <p className="text-sm text-primary font-medium mt-2">
          선택됨: {refImage.name}
        </p>
      )}
    </section>
  );
}

function ProductImageStep({
  productImage,
  onFileSelect,
  required,
}: {
  productImage: File | null;
  onFileSelect: (f: File | null) => void;
  required?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect]
  );

  return (
    <section>
      <StepLabel num={4} title="원본 이미지 업로드" sub={required ? '(필수)' : undefined} />
      <div
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="w-full h-48 border-2 border-dashed border-outline-variant rounded-2xl bg-surface-container-lowest flex flex-col items-center justify-center group hover:border-primary transition-all cursor-pointer shadow-sm"
      >
        <div className="w-14 h-14 rounded-full bg-surface-container-low flex items-center justify-center mb-4 group-hover:bg-primary-container/20 transition-colors">
          <span className="text-2xl text-outline">↑</span>
        </div>
        <p className="text-base font-bold text-on-surface-variant">
          {productImage ? productImage.name : '파일을 드래그하거나 클릭하여 업로드'}
        </p>
        <p className="text-xs text-outline mt-2 font-medium">JPEG, PNG up to 10MB</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          onFileSelect(file ?? null);
        }}
      />
    </section>
  );
}

function PromptStep({
  userPrompt,
  onChange,
}: {
  userPrompt: string;
  onChange: (v: string) => void;
}) {
  const appendKeyword = useCallback(
    (kw: string) => {
      onChange(userPrompt ? `${userPrompt} ${kw}` : kw);
    },
    [userPrompt, onChange]
  );

  return (
    <section className="pb-32">
      <StepLabel num={5} title="상세 요청 사항" />
      <div className="relative">
        <textarea
          value={userPrompt}
          onChange={(e) => onChange(e.target.value)}
          className="w-full h-56 bg-surface-container-lowest border-2 border-outline-variant/20 rounded-2xl p-7 font-body text-base text-on-surface placeholder:text-outline-variant/60 focus:ring-8 focus:ring-primary-fixed-dim/10 focus:border-primary transition-all resize-none shadow-sm outline-none"
          placeholder="생성하고 싶은 이미지의 특징을 자유롭게 적어주세요. (예: 아침 햇살이 비치는 화이트 톤의 카페 테이블)"
        />
      </div>
      <div className="mt-8 flex flex-wrap gap-3">
        {KEYWORD_CHIPS.map((kw) => (
          <button
            key={kw}
            onClick={() => appendKeyword(kw)}
            className="px-5 py-2.5 bg-secondary-container/50 text-on-secondary-container text-xs font-bold rounded-full hover:bg-primary-container hover:text-on-primary-container transition-all"
          >
            {kw}
          </button>
        ))}
      </div>
    </section>
  );
}

function PreviewCanvas({ previewUrl }: { previewUrl: string | null }) {
  return (
    <div className="w-2/5 bg-surface-dim/30 flex flex-col items-center justify-center relative border-r border-surface-container">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-surface-dim/20 pointer-events-none" />
      {previewUrl ? (
        <div className="w-full h-full flex items-center justify-center p-8">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="업로드된 이미지 미리보기"
            className="max-w-full max-h-full object-contain rounded-2xl shadow-lg"
          />
        </div>
      ) : (
        <div className="flex flex-col items-center gap-8 p-16 text-center opacity-40">
          <div className="w-32 h-32 rounded-[2rem] bg-surface-container-highest flex items-center justify-center shadow-inner">
            <span className="text-4xl text-outline">◻</span>
          </div>
          <div>
            <h3 className="font-headline text-xl font-bold text-on-surface">
              생성된 이미지가 여기에 표시됩니다
            </h3>
            <p className="mt-4 text-base text-on-surface-variant max-w-[280px] leading-relaxed">
              설정을 완료하고 하단의 생성 버튼을 클릭하여 프리미엄 이미지를 제작하세요.
            </p>
          </div>
        </div>
      )}
      <div className="absolute bottom-16 left-16">
        <span className="font-label text-[11px] tracking-[0.2em] text-outline uppercase font-bold">
          Preview Canvas / 01
        </span>
      </div>
    </div>
  );
}

// Main page
export default function GeneratorPage() {
  const router = useRouter();

  const [selectedSize, setSelectedSize] = useState<SizeValue>('square');
  const [selectedMood, setSelectedMood] = useState<MoodValue>('깔끔한 상품 홍보');
  const [refImage, setRefImage] = useState<File | null>(null);
  const [productImage, setProductImage] = useState<File | null>(null);
  const [userPrompt, setUserPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleProductImageSelect = useCallback((file: File | null) => {
    setProductImage(file);
    if (file) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }
  }, []);

  const handleSubmit = async () => {
    if (!productImage) {
      setErrorMsg('원본 이미지를 먼저 업로드해주세요.');
      return;
    }
    setIsLoading(true);
    try {
      const result: GenerateImageResponse = await generateImage({
        image: productImage ?? undefined,
        refImage: refImage ?? undefined,
        userPrompt: userPrompt || undefined,
        mood: selectedMood,
        subjectType: productImage ? 'product' : 'food',
        size: selectedSize,
      });

      const stored = {
        ...result,
        mood: selectedMood,
        size: selectedSize,
        userPrompt,
      };
      localStorage.setItem('generatorResult', JSON.stringify(stored));
      router.push('/result');
    } catch (error) {
      const msg = error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.';
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col font-body selection:bg-primary-container selection:text-on-primary-container">
      <NavBar />
      <main className="flex flex-1 overflow-hidden">
        <SideBar />
        <section className="flex-1 flex overflow-hidden">
          <PreviewCanvas previewUrl={previewUrl} />
          <div className="w-3/5 bg-surface overflow-y-auto">
            <div className="max-w-3xl mx-auto px-16 py-20">
              <header className="mb-20">
                <span className="font-label text-primary font-bold tracking-[0.2em] uppercase text-xs">
                  AI Creative Engine
                </span>
                <h1 className="mt-4 font-headline text-5xl font-extrabold text-on-surface tracking-tight leading-tight">
                  맞춤 이미지 만들기
                </h1>
                <p className="mt-4 text-on-surface-variant text-lg">
                  당신의 브랜드 가치를 담은 맞춤형 고품질 이미지를 생성합니다.
                </p>
              </header>
              <div className="space-y-20">
                <SizeStep selected={selectedSize} onChange={setSelectedSize} />
                <MoodStep selected={selectedMood} onChange={setSelectedMood} />
                <RefImageStep
                  refImage={refImage}
                  onFileSelect={setRefImage}
                  onClear={() => setRefImage(null)}
                />
                <ProductImageStep
                  productImage={productImage}
                  onFileSelect={handleProductImageSelect}
                  required
                />
                <PromptStep userPrompt={userPrompt} onChange={setUserPrompt} />
              </div>
              {errorMsg && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm font-medium whitespace-pre-wrap">
                  {errorMsg}
                </div>
              )}
              <div className="sticky bottom-12 mt-16 flex justify-end">
                <button
                  onClick={() => { setErrorMsg(null); handleSubmit(); }}
                  disabled={isLoading}
                  className="group flex items-center gap-5 px-14 py-6 bg-gradient-to-br from-primary to-primary-container text-on-primary rounded-2xl font-headline font-bold text-xl shadow-[0_20px_50px_-12px_rgba(41,102,120,0.4)] active:scale-95 transition-all disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  <span>{isLoading ? '생성 중...' : '이미지 생성하기'}</span>
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
