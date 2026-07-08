export type RuntimeConfig = {
  jobApiBaseUrl: string;
  candidateApiBaseUrl: string;
  environment: string;
};

const defaultConfig: RuntimeConfig = {
  jobApiBaseUrl: '/job-api/api/v1',
  candidateApiBaseUrl: '/candidate-api/api/v1',
  environment: 'local',
};

export function getRuntimeConfig(): RuntimeConfig {
  const fromWindow = window.__JOB_AGGREGATOR_CONFIG__ ?? {};
  return {
    jobApiBaseUrl: fromWindow.jobApiBaseUrl ?? defaultConfig.jobApiBaseUrl,
    candidateApiBaseUrl: fromWindow.candidateApiBaseUrl ?? defaultConfig.candidateApiBaseUrl,
    environment: fromWindow.environment ?? defaultConfig.environment,
  };
}
