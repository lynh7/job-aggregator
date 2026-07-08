// @ts-nocheck
import { Route, Switch } from 'wouter-preact';
import { AppShell } from 'src/components/app-shell';
import { HomePage } from 'src/pages/home-page';
import { JobsPage } from 'src/pages/jobs-page';
import { RawJobsPage } from 'src/pages/raw-jobs-page';
import { CandidatesPage } from 'src/pages/candidates-page';
import { TasksPage } from 'src/pages/tasks-page';
import { CandidateUploadPage } from 'src/pages/candidate-upload-page';
import { CandidateLookupPage } from 'src/pages/candidate-lookup-page';

export function App() {
  return (
    <AppShell>
      <Switch>
        <Route path="/" component={HomePage} />
        <Route path="/jobs" component={JobsPage} />
        <Route path="/candidate/upload" component={CandidateUploadPage} />
        <Route path="/candidate/lookup" component={CandidateLookupPage} />
        <Route path="/admin/jobs" component={JobsPage} />
        <Route path="/admin/raw-jobs" component={RawJobsPage} />
        <Route path="/admin/candidates" component={CandidatesPage} />
        <Route path="/admin/tasks" component={TasksPage} />
        <Route component={HomePage} />
      </Switch>
    </AppShell>
  );
}
