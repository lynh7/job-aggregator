import { SectionCard } from 'src/components/section-card';
import { ResourceState } from 'src/components/resource-state';
import { getRuntimeConfig } from 'src/lib/config';
import { useJsonResource } from 'src/lib/http';
import { RawJob } from 'src/lib/types';

export function RawJobsPage() {
  const config = getRuntimeConfig();
  const rawJobs = useJsonResource<RawJob[]>(() => `${config.jobApiBaseUrl}/raw-jobs?limit=50`, []);

  return (
    <SectionCard title="Raw Jobs" subtitle="Provider payload browser for admin inspection">
      <div class="toolbar-row">
        <sl-button onClick={rawJobs.refresh}>Refresh</sl-button>
      </div>
      <ResourceState loading={rawJobs.loading} error={rawJobs.error} empty={!rawJobs.loading && !rawJobs.error && (rawJobs.data?.length ?? 0) === 0}>
        <div class="card-grid">
          {(rawJobs.data ?? []).map((record) => (
            <sl-card key={record.id} class="json-card">
              <div slot="header" class="json-header">
                <strong>{record.provider}</strong>
                <sl-badge>{record.api_version}</sl-badge>
              </div>
              <p class="monospace">source_record_id: {record.source_record_id}</p>
              <p class="muted">Fetched: {new Date(record.fetched_at).toLocaleString()}</p>
              <sl-details summary="Payload JSON">
                <pre>{JSON.stringify(record.payload, null, 2)}</pre>
              </sl-details>
            </sl-card>
          ))}
        </div>
      </ResourceState>
    </SectionCard>
  );
}
