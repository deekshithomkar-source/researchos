const loopbackHosts = new Set(['localhost', '127.0.0.1', '[::1]']);

export function resolveApiRoot(configuredUrl, pageUrl, development = false) {
  const page = new URL(pageUrl);
  const api = new URL(configuredUrl || `${page.protocol}//${page.hostname}:8000`, page);
  // Local host aliases are different cookie sites. Keep development sessions
  // on the browser's site while preserving the configured API port and path.
  if (development && loopbackHosts.has(page.hostname) && loopbackHosts.has(api.hostname)) {
    api.hostname = page.hostname;
    api.protocol = page.protocol;
  }
  return api.href.replace(/\/$/, '').replace(/\/api$/, '');
}
