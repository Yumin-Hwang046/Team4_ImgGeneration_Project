import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Nordic Muse',
  description: 'AI-powered ad image generator for small businesses',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
