import type { ReviewJob, IncidentJob } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getReviews(): Promise<ReviewJob[]> {
  const res = await fetch(`${API_BASE}/api/reviews`);
  if (!res.ok) throw new Error('Failed to fetch reviews');
  return res.json();
}

export async function getIncidents(): Promise<IncidentJob[]> {
  const res = await fetch(`${API_BASE}/api/incidents`);
  if (!res.ok) throw new Error('Failed to fetch incidents');
  return res.json();
}
