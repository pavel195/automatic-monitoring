const apiOrigin = window.location.port === '4200'
  ? window.location.origin.replace(/:4200$/, ':8000')
  : window.location.origin;

export const environment = {
  production: true,
  apiUrl: `${apiOrigin}/api`
};
