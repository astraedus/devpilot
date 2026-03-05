'use client';

import { useEffect, useState, useCallback } from 'react';
import { getReviews, getIncidents } from '../lib/api';
import type { ReviewJob, IncidentJob, PRReview, IncidentReport } from '../lib/types';

// ---- Utility helpers ----

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return 'unknown time';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

function parseResult<T>(json: string | null): T | null {
  if (!json) return null;
  try {
    return JSON.parse(json) as T;
  } catch {
    return null;
  }
}

// ---- Badge components ----

function HCSBadge({ url }: { url: string }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 7px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 600,
        background: '#0c1a2e',
        color: '#38bdf8',
        border: '1px solid #1e3a5f',
        textDecoration: 'none',
        letterSpacing: '0.03em',
        flexShrink: 0,
      }}
      title="Verified on Hedera Consensus Service"
    >
      <span style={{ fontSize: '9px' }}>&#9632;</span> HCS
    </a>
  );
}


function VerdictBadge({ verdict }: { verdict: string }) {
  const styles: Record<string, { background: string; color: string; label: string }> = {
    approve: { background: '#14532d', color: '#4ade80', label: 'Approved' },
    request_changes: { background: '#450a0a', color: '#f87171', label: 'Changes Requested' },
    comment: { background: '#1c1917', color: '#fbbf24', label: 'Comment' },
  };
  const style = styles[verdict] ?? { background: '#1c1917', color: '#888', label: verdict };
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 600,
        background: style.background,
        color: style.color,
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
      }}
    >
      {style.label}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, { background: string; color: string }> = {
    critical: { background: '#450a0a', color: '#f87171' },
    high: { background: '#431407', color: '#fb923c' },
    medium: { background: '#1c1917', color: '#fbbf24' },
  };
  const style = styles[severity] ?? { background: '#1c1917', color: '#888' };
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '11px',
        fontWeight: 600,
        background: style.background,
        color: style.color,
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
      }}
    >
      {severity}
    </span>
  );
}

function StatusDot({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    done: '#4ade80',
    running: '#5b9cf6',
    pending: '#888',
    error: '#f87171',
  };
  return (
    <span
      style={{
        display: 'inline-block',
        width: '7px',
        height: '7px',
        borderRadius: '50%',
        background: colorMap[status] ?? '#888',
        flexShrink: 0,
      }}
    />
  );
}

// ---- Skeleton loader ----

function SkeletonCard() {
  return (
    <div
      style={{
        background: '#141414',
        border: '1px solid #222',
        borderRadius: '8px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      {[80, 60, 40].map((w, i) => (
        <div
          key={i}
          style={{
            height: '12px',
            width: `${w}%`,
            background: '#1e1e1e',
            borderRadius: '4px',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}
        />
      ))}
    </div>
  );
}

// ---- PR Review Card ----

function ReviewCard({ job }: { job: ReviewJob }) {
  const review = parseResult<PRReview>(job.result_json);
  const shortRepo = job.repo.split('/').slice(-2).join('/');
  const hcsUrl = job.hcs_url ?? null;

  return (
    <div
      style={{
        background: '#141414',
        border: '1px solid #222',
        borderRadius: '8px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        transition: 'border-color 0.15s',
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.borderColor = '#333')}
      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.borderColor = '#222')}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
          <StatusDot status={job.status} />
          <span
            style={{
              fontWeight: 600,
              fontSize: '13px',
              color: '#f5f5f5',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {shortRepo}
          </span>
          <span style={{ color: '#888', fontSize: '12px', flexShrink: 0 }}>PR #{job.pr_number}</span>
        </div>
        {review && <VerdictBadge verdict={review.overall} />}
      </div>

      {review?.summary && (
        <p
          style={{
            color: '#ccc',
            fontSize: '13px',
            lineHeight: '1.5',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {review.summary}
        </p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {review?.issues && review.issues.length > 0 ? (
            <span style={{ fontSize: '12px', color: '#888' }}>
              {review.issues.length} issue{review.issues.length !== 1 ? 's' : ''} found
            </span>
          ) : (
            <span style={{ fontSize: '12px', color: '#888' }}>No issues</span>
          )}
          {hcsUrl && <HCSBadge url={hcsUrl} />}
        </div>
        <span style={{ fontSize: '11px', color: '#555' }}>{timeAgo(job.created_at)}</span>
      </div>
    </div>
  );
}

// ---- CI Incident Card ----

function IncidentCard({ job }: { job: IncidentJob }) {
  const report = parseResult<IncidentReport>(job.result_json);
  const shortRepo = job.repo.split('/').slice(-2).join('/');
  const hcsUrl = job.hcs_url ?? null;

  return (
    <div
      style={{
        background: '#141414',
        border: '1px solid #222',
        borderRadius: '8px',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        transition: 'border-color 0.15s',
      }}
      onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.borderColor = '#333')}
      onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.borderColor = '#222')}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
          <StatusDot status={job.status} />
          <span
            style={{
              fontWeight: 600,
              fontSize: '13px',
              color: '#f5f5f5',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {shortRepo}
          </span>
          <span style={{ color: '#888', fontSize: '12px', flexShrink: 0 }}>Run #{job.run_id}</span>
        </div>
        {report && <SeverityBadge severity={report.severity} />}
      </div>

      {report?.root_cause && (
        <p
          style={{
            color: '#ccc',
            fontSize: '13px',
            lineHeight: '1.5',
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {report.root_cause}
        </p>
      )}

      {report?.affected_files && report.affected_files.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
          {report.affected_files.slice(0, 3).map((f) => (
            <span
              key={f}
              style={{
                fontSize: '11px',
                color: '#888',
                background: '#1a1a1a',
                border: '1px solid #2a2a2a',
                borderRadius: '3px',
                padding: '1px 6px',
                fontFamily: 'monospace',
              }}
            >
              {f.split('/').pop()}
            </span>
          ))}
          {report.affected_files.length > 3 && (
            <span style={{ fontSize: '11px', color: '#555' }}>+{report.affected_files.length - 3} more</span>
          )}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>{hcsUrl && <HCSBadge url={hcsUrl} />}</div>
        <span style={{ fontSize: '11px', color: '#555' }}>{timeAgo(job.created_at)}</span>
      </div>
    </div>
  );
}

// ---- Section wrapper ----

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingBottom: '4px', borderBottom: '1px solid #1a1a1a' }}>
        <h2 style={{ fontSize: '13px', fontWeight: 600, color: '#f5f5f5', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {title}
        </h2>
        {count !== undefined && (
          <span
            style={{
              fontSize: '11px',
              color: '#888',
              background: '#1e1e1e',
              border: '1px solid #2a2a2a',
              borderRadius: '10px',
              padding: '1px 7px',
              fontWeight: 500,
            }}
          >
            {count}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}

// ---- Main page ----

export default function DashboardPage() {
  const [reviews, setReviews] = useState<ReviewJob[] | null>(null);
  const [incidents, setIncidents] = useState<IncidentJob[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const [r, i] = await Promise.all([getReviews(), getIncidents()]);
      setReviews(r);
      setIncidents(i);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const isLoading = reviews === null && incidents === null && error === null;

  return (
    <>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>

      <div
        style={{
          maxWidth: '1200px',
          margin: '0 auto',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        {error && (
          <div
            style={{
              background: '#450a0a',
              border: '1px solid #7f1d1d',
              borderRadius: '6px',
              padding: '10px 14px',
              color: '#fca5a5',
              fontSize: '13px',
              marginBottom: '8px',
            }}
          >
            Could not reach backend: {error}
          </div>
        )}

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
            gap: '32px',
            alignItems: 'start',
          }}
        >
          {/* PR Reviews */}
          <Section title="PR Reviews" count={reviews?.length}>
            {isLoading ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : reviews && reviews.length > 0 ? (
              reviews.map((job) => <ReviewCard key={job.id ?? job.pr_number} job={job} />)
            ) : (
              <div
                style={{
                  color: '#555',
                  fontSize: '13px',
                  textAlign: 'center',
                  padding: '40px 0',
                  background: '#111',
                  borderRadius: '8px',
                  border: '1px dashed #222',
                }}
              >
                No reviews yet
              </div>
            )}
          </Section>

          {/* CI Incidents */}
          <Section title="CI Incidents" count={incidents?.length}>
            {isLoading ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : incidents && incidents.length > 0 ? (
              incidents.map((job) => <IncidentCard key={job.id ?? job.run_id} job={job} />)
            ) : (
              <div
                style={{
                  color: '#555',
                  fontSize: '13px',
                  textAlign: 'center',
                  padding: '40px 0',
                  background: '#111',
                  borderRadius: '8px',
                  border: '1px dashed #222',
                }}
              >
                No incidents yet
              </div>
            )}
          </Section>
        </div>
      </div>
    </>
  );
}
