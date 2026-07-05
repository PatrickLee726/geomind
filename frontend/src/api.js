import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export default {
  // 通用
  get: (path) => api.get(path),

  // 案例
  getCases: () => api.get('/cases'),
  getCase: (id) => api.get(`/cases/${id}`),
  getCaseSchema: (id) => api.get(`/cases/${id}/schema`),

  // 数据
  uploadTroposphere: (formData) => api.post('/data/upload/troposphere', formData),
  uploadCSV: (formData) => api.post('/data/upload/csv', formData),
  uploadFile: (formData) => api.post('/data/upload/generic', formData),
  fetchIGSTropo: (data) => api.post('/data/igs/troposphere', data),
  getIGSStations: () => api.get('/data/igs/stations'),

  // 任务
  submitJob: (data) => api.post('/jobs', data),
  getJob: (id) => api.get(`/jobs/${id}`),
  listJobs: () => api.get('/jobs'),

  // 结果
  getResult: (id) => api.get(`/results/${id}`),
  getChart: (jobId, name) => `/api/results/${jobId}/chart/${name}`,
}
