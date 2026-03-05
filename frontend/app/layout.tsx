import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DevPilot',
  description: 'AI-powered GitHub PR review and CI incident triage',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header
          style={{
            borderBottom: '1px solid #222',
            padding: '16px 24px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <circle cx="10" cy="10" r="9" stroke="#5b9cf6" strokeWidth="1.5" />
            <path
              d="M6 10l3 3 5-5"
              stroke="#5b9cf6"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span
            style={{
              fontWeight: 600,
              fontSize: '15px',
              color: '#f5f5f5',
              letterSpacing: '-0.01em',
            }}
          >
            DevPilot
          </span>
          <span
            style={{
              fontSize: '12px',
              color: '#888',
              marginLeft: '4px',
            }}
          >
            AI PR Review + CI Triage
          </span>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
