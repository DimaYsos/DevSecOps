import axios from 'axios';

const API_BASE = '/api/v2';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  if (csrfToken) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

export const auth = {
  csrf: () => api.get('/auth/csrf/'),
  login: (data) => api.post('/auth/login/', data),
  logout: () => api.post('/auth/logout/'),
  register: (data) => api.post('/auth/register/', data),
  me: () => api.get('/users/me/'),
  resetRequest: (data) => api.post('/auth/password-reset/', data),
  resetConfirm: (data) => api.post('/auth/password-reset/confirm/', data),
  changePassword: (data) => api.post('/auth/change-password/', data),
};

export const users = {
  list: (params) => api.get('/users/', { params }),
  get: (id) => api.get(`/users/${id}/`),
  update: (id, data) => api.patch(`/users/${id}/`, data),
  promote: (id, data) => api.post(`/users/${id}/promote/`, data),
};

export const organizations = {
  list: () => api.get('/organizations/'),
  get: (id) => api.get(`/organizations/${id}/`),
};

export const tickets = {
  list: (params) => api.get('/tickets/', { params }),
  get: (id) => api.get(`/tickets/${id}/`),
  create: (data) => api.post('/tickets/', data),
  update: (id, data) => api.patch(`/tickets/${id}/`, data),
  transition: (id, data) => api.post(`/tickets/${id}/transition/`, data),
  escalate: (id) => api.post(`/tickets/${id}/escalate/`),
  search: (params) => api.get('/search/advanced/', { params }),
};

export const incidents = {
  list: (params) => api.get('/incidents/', { params }),
  get: (id) => api.get(`/incidents/${id}/`),
  create: (data) => api.post('/incidents/', data),
  update: (id, data) => api.patch(`/incidents/${id}/`, data),
};

export const comments = {
  list: (params) => api.get('/comments/', { params }),
  create: (data) => api.post('/comments/', data),
  update: (id, data) => api.patch(`/comments/${id}/`, data),
  delete: (id) => api.delete(`/comments/${id}/`),
};

export const attachments = {
  list: (params) => api.get('/attachments/', { params }),
  upload: (formData) => api.post('/attachments/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  delete: (id) => api.delete(`/attachments/${id}/`),
};

export const assets = {
  list: (params) => api.get('/assets/', { params }),
  get: (id) => api.get(`/assets/${id}/`),
  create: (data) => api.post('/assets/', data),
  update: (id, data) => api.patch(`/assets/${id}/`, data),
  importCsv: (formData) => api.post('/assets/import_csv/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  importData: (formData) => api.post('/assets/import_data/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  exportCsv: () => api.get('/assets/export_csv/', { responseType: 'blob' }),
};

export const reports = {
  list: () => api.get('/report-jobs/'),
  create: (data) => api.post('/report-jobs/', data),
  preview: (data) => api.post('/reports/preview/', data),
  files: () => api.get('/reports/files/'),
};

export const imports = {
  list: () => api.get('/import-jobs/'),
  create: (formData) => api.post('/import-jobs/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
};

export const webhooks = {
  list: () => api.get('/webhook-configs/'),
  get: (id) => api.get(`/webhook-configs/${id}/`),
  create: (data) => api.post('/webhook-configs/', data),
  update: (id, data) => api.patch(`/webhook-configs/${id}/`, data),
  test: (id) => api.post(`/webhook-configs/${id}/test/`),
  deliveries: (id) => api.get(`/webhook-configs/${id}/deliveries/`),
};

export const audit = {
  list: (params) => api.get('/audit-events/', { params }),
};

export const enrichment = {
  enrichUser: (data) => api.post('/enrichment/user/', data),
  enrichAsset: (data) => api.post('/enrichment/asset/', data),
};

export const tokens = {
  list: () => api.get('/tokens/'),
  create: (data) => api.post('/tokens/', data),
  delete: (id) => api.delete(`/tokens/${id}/`),
};

export default api;
