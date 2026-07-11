// @ts-nocheck
import { SectionCard } from 'src/components/section-card';
import { ResourceState } from 'src/components/resource-state';
import { getRuntimeConfig } from 'src/lib/config';
import { useJsonResource } from 'src/lib/http';
import { Candidate } from 'src/lib/types';

export function CandidatesPage() {
  const config = getRuntimeConfig();
  const candidates = useJsonResource<Candidate[]>(() => `${config.candidateApiBaseUrl}/candidates?limit=100`, []);

  return (
    <SectionCard title="Candidates" subtitle="Candidate submission inventory">
      <div class="toolbar-row">
        <button type="button" class="primary-button" onClick={candidates.refresh}>Refresh</button>
      </div>
      <ResourceState loading={candidates.loading} error={candidates.error} empty={!candidates.loading && !candidates.error && (candidates.data?.length ?? 0) === 0}>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Status</th>
                <th>Email</th>
                <th>Location</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {(candidates.data ?? []).map((candidate) => (
                <tr key={candidate.id}>
                  <td>{candidate.id}</td>
                  <td>{candidate.full_name ?? '—'}</td>
                  <td><sl-badge variant="primary">{candidate.status}</sl-badge></td>
                  <td>{candidate.email ?? '—'}</td>
                  <td>{candidate.location ?? '—'}</td>
                  <td>{new Date(candidate.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ResourceState>
    </SectionCard>
  );
}
