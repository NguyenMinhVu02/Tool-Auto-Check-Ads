export function toolStatus(item) {
  if (!item.installed) return item.required ? 'missing' : 'optional';
  if (item.ai && item.logged_in === false) return 'login';
  return 'ok';
}

export function setupSummary(status) {
  const items = status?.items || [];
  const missingRequired = items.filter((item) => item.required && !item.installed).map((item) => item.id);
  const aiInstalled = items.some((item) => item.ai && item.installed);
  const installAll = [...missingRequired, ...(aiInstalled || !items.some((item) => item.id === 'claude') ? [] : ['claude'])];
  return {
    ready: Boolean(status?.ready),
    missingRequired: installAll,
    installAll,
    needsLoginHint: items.some((item) => item.ai && item.installed && item.logged_in !== true),
  };
}
