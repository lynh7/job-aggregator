// @ts-nocheck
import { useMemo, useState } from 'preact/hooks';
import { SectionCard } from 'src/components/section-card';
import { ResourceState } from 'src/components/resource-state';
import { getRuntimeConfig } from 'src/lib/config';
import { useJsonResource } from 'src/lib/http';
import { Job } from 'src/lib/types';

export function JobsPage() {
  const config = getRuntimeConfig();
  const [query, setQuery] = useState('');
  const jobs = useJsonResource<Job[]>(() => `${config.jobApiBaseUrl}/jobs?limit=100`, []);

  const filtered = useMemo(() => {
    const search = query.trim().toLowerCase();
    if (!search) {
      return jobs.data ?? [];
    }
    return (jobs.data ?? []).filter((job) =>
      [job.title, job.company, job.location, job.provider]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(search)),
    );
  }, [jobs.data, query]);

  return (
    <SectionCard title="Jobs" subtitle="Normalized job records from the core API">
      <div class="toolbar-row">
        <input
          class="text-input"
          placeholder="Filter by title, company, provider, location"
          value={query}
          onInput={(event) => setQuery((event.currentTarget as HTMLInputElement).value)}
        />
        <button type="button" class="primary-button" onClick={jobs.refresh}>Refresh</button>
      </div>
      <ResourceState loading={jobs.loading} error={jobs.error} empty={!jobs.loading && !jobs.error && filtered.length === 0}>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Provider</th>
                <th>Company</th>
                <th>Location</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((job) => (
                <tr key={job.id}>
                  <td>
                    <a href={job.url} target="_blank" rel="noreferrer">
                      {job.title}
                    </a>
                  </td>
                  <td>{job.provider}</td>
                  <td>{job.company ?? '—'}</td>
                  <td>{job.location ?? '—'}</td>
                  <td><sl-badge variant="neutral">{job.normalization_status}</sl-badge></td>
                  <td>{new Date(job.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ResourceState>
    </SectionCard>
  );
}
