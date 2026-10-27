export const intelligenceTabs = [['datasets', 'Datasets'], ['skills', 'Skills'], ['courses', 'Courses'], ['projects', 'Projects'], ['internships', 'Internships'], ['career_paths', 'Career Paths'], ['next_steps', 'Next Steps']];
export function safeResourceUrl(value) {
  try { const url = new URL(value); return url.protocol === 'https:' ? url.href : null; } catch { return null; }
}
export function resourceStatus(status) {
  return ({ invalid_response: 'Provider returned invalid metadata; no unverified listings are shown', verified: 'Verified at the recorded check time', partial: 'Partial results: some checks failed', no_verified_matches: 'No verified matches found', provider_unavailable: 'Provider unavailable; no unverified listings are shown' })[status] || 'Not checked';
}
