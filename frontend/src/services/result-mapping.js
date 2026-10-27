/** @template {keyof import('./result-contract').CanonicalResearchResult} K
 * @param {import('./result-contract').CanonicalResearchResult | null | undefined} modules
 * @param {K} section
 * @returns {import('./result-contract').CanonicalResearchResult[K]}
 */
export function sectionData(modules, section) {
  // No fallback to summary, sources, or another tab's content.
  return modules?.[section] ?? /** @type {any} */ ([]);
}
