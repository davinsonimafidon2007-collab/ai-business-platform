import { api } from './api/client';
import type {
  InspectionSession,
  InspectionSessionDetail,
  InspectionSummary,
  CreateSessionRequest,
  UpdateObservationRequest,
  UploadPhotoRequest,
  InspectionObservation,
  InspectionPhoto,
  VisionAnalysis,
} from '../types/inspection';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const inspectionService = {
  async createSession(data: CreateSessionRequest): Promise<InspectionSession> {
    const { data: result } = await api.post<InspectionSession>('/inspections', data);
    return result;
  },

  async getSession(sessionId: string): Promise<InspectionSessionDetail> {
    const { data: result } = await api.get<InspectionSessionDetail>(`/inspections/${sessionId}`);
    return result;
  },

  async updateItem(
    sessionId: string,
    data: UpdateObservationRequest,
  ): Promise<InspectionObservation> {
    const { data: result } = await api.put<InspectionObservation>(`/inspections/${sessionId}/items`, data);
    return result;
  },

  async uploadPhoto(
    sessionId: string,
    data: UploadPhotoRequest,
  ): Promise<InspectionPhoto> {
    const { data: result } = await api.post<InspectionPhoto>(`/inspections/${sessionId}/photos`, data);
    return result;
  },

  /**
   * Uploads a photo file via multipart/form-data.
   * This is the endpoint used from the mobile camera capture.
   * Includes Authorization header from localStorage.
   */
  async uploadPhotoFile(
    sessionId: string,
    observationId: string,
    file: File,
  ): Promise<InspectionPhoto> {
    const formData = new FormData();
    formData.append('file', file);

    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(
      `${API_BASE_URL}/api/v1/inspections/${sessionId}/photos/upload?observation_id=${observationId}`,
      {
        method: 'POST',
        headers,
        credentials: 'include',
      },
    );

    if (!response.ok) {
      throw new Error(`Error uploading photo: ${response.statusText}`);
    }

    return response.json();
  },

  async finalizeSession(sessionId: string): Promise<InspectionSession> {
    const { data: result } = await api.post<InspectionSession>(`/inspections/${sessionId}/finalize`);
    return result;
  },

  async getSummary(sessionId: string): Promise<InspectionSummary> {
    const { data: result } = await api.get<InspectionSummary>(`/inspections/${sessionId}/summary`);
    return result;
  },

  async analyzePhotos(sessionId: string): Promise<VisionAnalysis> {
    const { data: result } = await api.post<VisionAnalysis>(`/inspections/${sessionId}/analyze`, {});
    return result;
  },
};
