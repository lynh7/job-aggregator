// @ts-nocheck
import { SectionCard } from 'src/components/section-card';
import { ResourceState } from 'src/components/resource-state';
import { getRuntimeConfig } from 'src/lib/config';
import { useJsonResource } from 'src/lib/http';
import { CandidateTask } from 'src/lib/types';

export function TasksPage() {
  const config = getRuntimeConfig();
  const tasks = useJsonResource<CandidateTask[]>(() => `${config.candidateApiBaseUrl}/tasks?limit=100`, []);

  return (
    <SectionCard title="Tasks" subtitle="Background queue visibility for administrators">
      <div class="toolbar-row">
        <button type="button" class="primary-button" onClick={tasks.refresh}>Refresh</button>
      </div>
      <ResourceState loading={tasks.loading} error={tasks.error} empty={!tasks.loading && !tasks.error && (tasks.data?.length ?? 0) === 0}>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Status</th>
                <th>Candidate</th>
                <th>Attempts</th>
                <th>Available</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {(tasks.data ?? []).map((task) => (
                <tr key={task.id}>
                  <td>{task.id}</td>
                  <td>{task.task_type}</td>
                  <td><sl-badge>{task.status}</sl-badge></td>
                  <td>{task.candidate_id ?? '—'}</td>
                  <td>{task.attempts}/{task.max_attempts}</td>
                  <td>{new Date(task.available_at).toLocaleString()}</td>
                  <td>{task.last_error ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ResourceState>
    </SectionCard>
  );
}
