// @ts-nocheck
import { SectionCard } from 'src/components/section-card';
import { StatCard } from 'src/components/stat-card';
import { ResourceState } from 'src/components/resource-state';
import { getRuntimeConfig } from 'src/lib/config';
import { useJsonResource } from 'src/lib/http';
import { Candidate, CandidateTask, Job, RawJob } from 'src/lib/types';

export function HomePage() {
  const config = getRuntimeConfig();
  const jobs = useJsonResource<Job[]>(() => `${config.jobApiBaseUrl}/jobs?limit=25`, []);
  const rawJobs = useJsonResource<RawJob[]>(() => `${config.jobApiBaseUrl}/raw-jobs?limit=25`, []);
  const candidates = useJsonResource<Candidate[]>(() => `${config.candidateApiBaseUrl}/candidates?limit=25`, []);
  const tasks = useJsonResource<CandidateTask[]>(() => `${config.candidateApiBaseUrl}/tasks?limit=25`, []);

  return (
    <div class="page-grid">
      <section class="hero-banner">
        <div>
          <p class="eyebrow">UI-only service</p>
          <h3>One thin client for candidates and administrators</h3>
          <p>
            This SPA renders data from the existing core and candidate APIs. It does not perform
            scoring, normalization, or permission logic in the browser.
          </p>
        </div>
      </section>

      <div class="stats-grid">
        <StatCard label="Jobs" value={jobs.data?.length ?? '…'} hint="Latest normalized records" />
        <StatCard label="Raw Jobs" value={rawJobs.data?.length ?? '…'} hint="Latest provider payloads" />
        <StatCard label="Candidates" value={candidates.data?.length ?? '…'} hint="Latest submissions" />
        <StatCard label="Tasks" value={tasks.data?.length ?? '…'} hint="Background work queue" />
      </div>

      <SectionCard title="Why this UI exists" subtitle="Frontend concerns only">
        <ul class="bullet-list">
          <li>Candidate workflows: upload CV, inspect matches, submit applications.</li>
          <li>Admin workflows: inspect jobs, raw payloads, candidate state, task failures, and trigger crawl runs.</li>
          <li>Runtime API URLs are injected by the container at startup, not hardcoded in the bundle.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Current crawl milestone" subtitle="Operational path available today">
        <ul class="bullet-list">
          <li>Administrators can trigger keyword-based multi-provider crawl from the UI.</li>
          <li>Crawler API fetches provider data, then sends raw records into job-api ingest.</li>
          <li>Candidate self-serve search and personalization remains a later product step.</li>
        </ul>
      </SectionCard>

      <SectionCard title="Recent activity" subtitle="Latest jobs and candidate submissions">
        <ResourceState loading={jobs.loading || candidates.loading} error={jobs.error ?? candidates.error}>
          <div class="split-grid">
            <div>
              <h4>Latest jobs</h4>
              <ul class="compact-list">
                {(jobs.data ?? []).slice(0, 5).map((job) => (
                  <li key={job.id}>
                    <strong>{job.title}</strong>
                    <span>{job.provider} · {job.location ?? 'Unknown location'}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4>Latest candidates</h4>
              <ul class="compact-list">
                {(candidates.data ?? []).slice(0, 5).map((candidate) => (
                  <li key={candidate.id}>
                    <strong>{candidate.full_name ?? `Candidate #${candidate.id}`}</strong>
                    <span>{candidate.status} · {candidate.email ?? 'No email'}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </ResourceState>
      </SectionCard>
    </div>
  );
}
