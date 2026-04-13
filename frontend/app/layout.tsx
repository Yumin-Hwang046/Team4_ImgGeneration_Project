import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'The Digital Curator | AI 인스타그램 큐레이션',
  description: 'AI로 완성하는 브랜드 감성 콘텐츠. 생성부터 자동 업로드까지.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko" className="light">
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
        />
      </head>
      <body className="bg-background text-on-surface antialiased">
        {children}
      </body>
    </html>
  )
}
