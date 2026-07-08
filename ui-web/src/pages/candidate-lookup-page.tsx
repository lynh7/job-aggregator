// @ts-nocheck
import { useMemo, useState } from 'preact/hooks';
import { SectionCard } from 'src/components/section-card';
import { ResourceState } from 'src/components/resource-state';
import { getRuntimeConfig } from 'src/lib/config';
import { useJsonResource } from 'src/lib/http';
import { CandidateApplication, CandidateDetail, CandidateMatch } from 'src/lib/types';

export function CandidateLookupPage() {
  const config = getRuntimeConfig();
  const [candidateIdInput, setCandidateIdInput] = useState('');
  const candidateId = useMemo(() => {
    const parsed = Number(candidateIdInput);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
  }, [candidateIdInput]);

  const detail = useJsonResource<CandidateDetail>(
    () => (candidateId ? `${config.candidateApiBaseUrl}/candidates/${candidateId}` : null),
    [candidateId],
  );
  const matches = useJsonResource<CandidateMatch[]>(
    () => (candidateId ? `${config.candidateApiBaseUrl}/candidates/${candidateId}/matches` : null),
    [candidateId],
  );
  const applications = useJsonResource<CandidateApplication[]>(
    () => (candidateId ? `${config.candidateApiBaseUrl}/candidates/${candidateId}/applications` : null),
    [candidateId],
  );

  return (
    <div class="page-grid">
      <SectionCard title="Candidate Lookup" subtitle="Load one candidate and render backend-provided profile, matches, and applications">
        <div class="toolbar-row">
          <input
            class="text-input"
            placeholder="Enter candidate ID"
            value={candidateIdInput}
            onInput={(event) => setCandidateIdInput((event.currentTarget as HTMLInputElement).value)}
          />
          <sl-button onClick={() => { detail.refresh(); matches.refresh(); applications.refresh(); }} disabled={!candidateId}>Load</sl-button>
        </div>
      </SectionCard>

      <SectionCard title="Candidate Profile">
        <ResourceState loading={detail.loading} error={detail.error} empty={!candidateId}>
          {detail.data ? (
            <div class="split-grid">
              <div>
                <p><strong>Name:</strong> {detail.data.candidate.full_name ?? '—'}</p>
                <p><strong>Status:</strong> {detail.data.candidate.status}</p>
                <p><strong>Email:</strong> {detail.data.candidate.email ?? '—'}</p>
                <p><strong>Location:</strong> {detail.data.candidate.location ?? '—'}</p>
              </div>
              <div>
                <p><strong>Summary:</strong> {detail.data.latest_profile?.summary ?? 'No parsed profile yet.'}</p>
                <p><strong>Skills:</strong> {(detail.data.latest_profile?.skills ?? []).join(', ') || '—'}</p>
                <p><strong>Languages:</strong> {(detail.data.latest_profile?.languages ?? []).join(', ') || '—'}</p>
              </div>
            </div>
          ) : null}
        </ResourceState>
      </SectionCard>

      <SectionCard title="Matches">
        <ResourceState loading={matches.loading} error={matches.error} empty={!candidateId || (matches.data?.length ?? 0) === 0}>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Provider</th>
                  <th>Score</th>
                  <th>Matched skills</th>
                  <th>Missing skills</th>
                </tr>
              </thead>
              <tbody>
                {(matches.data ?? []).map((match) => (
                  <tr key={match.id}>
                    <td>{match.title}</td>
                    <td>{match.provider}</td>
                    <td>{match.match_score}</td>
                    <td>{match.matched_skills.join(', ') || '—'}</td>
                    <td>{match.missing_skills.join(', ') || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ResourceState>
      </SectionCard>

      <SectionCard title="Applications">
        <ResourceState loading={applications.loading} error={applications.error} empty={!candidateId || (applications.data?.length ?? 0) === 0}>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Applied at</th>
                  <th>External ID</th>
                </tr>
              </thead>
              <tbody>
                {(applications.data ?? []).map((application) => (
                  <tr key={application.id}>
                    <td>{application.id}</td>
                    <td>{application.provider}</td>
                    <td>{application.status}</td>
                    <td>{application.applied_at ? new Date(application.applied_at).toLocaleString() : '—'}</td>
                    <td>{application.external_application_id ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ResourceState>
      </SectionCard>
    </div>
  );
}
