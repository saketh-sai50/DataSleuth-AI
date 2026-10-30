import axios from 'axios';
import {
  Dataset,
  DatasetListResponse,
  Investigation,
  Report,
  ChatResponse,
} from '../types';

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const datasetsApi = {
  upload: async (file: File): Promise<Dataset> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<Dataset>('/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },
  list: async (): Promise<DatasetListResponse> => {
    const res = await apiClient.get<DatasetListResponse>('/datasets/');
    return res.data;
  },
  get: async (id: number): Promise<Dataset> => {
    const res = await apiClient.get<Dataset>(`/datasets/${id}`);
    return res.data;
  },
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/datasets/${id}`);
  },
};

export const investigationsApi = {
  analyze: async (question: string, datasetIds: number[]): Promise<any> => {
    const res = await apiClient.post('/investigations/analyze', {
      question,
      dataset_ids: datasetIds,
    });
    return res.data;
  },
  list: async (): Promise<Investigation[]> => {
    const res = await apiClient.get<Investigation[]>('/investigations/');
    return res.data;
  },
  get: async (id: number): Promise<Investigation> => {
    const res = await apiClient.get<Investigation>(`/investigations/${id}`);
    return res.data;
  },
  continue: async (investigationId: number, newDatasetIds: number[]): Promise<any> => {
    const res = await apiClient.post('/investigations/continue', {
      investigation_id: investigationId,
      new_dataset_ids: newDatasetIds,
    });
    return res.data;
  },
};

export const reportsApi = {
  generate: async (investigationId: number): Promise<Report> => {
    const res = await apiClient.post<Report>('/reports/generate', {
      investigation_id: investigationId,
    });
    return res.data;
  },
  list: async (): Promise<Report[]> => {
    const res = await apiClient.get<Report[]>('/reports/');
    return res.data;
  },
  get: async (id: number): Promise<Report> => {
    const res = await apiClient.get<Report>(`/reports/${id}`);
    return res.data;
  },
  chat: async (message: string, investigationId?: number): Promise<ChatResponse> => {
    const res = await apiClient.post<ChatResponse>('/reports/chat', {
      message,
      investigation_id: investigationId,
    });
    return res.data;
  },
};
