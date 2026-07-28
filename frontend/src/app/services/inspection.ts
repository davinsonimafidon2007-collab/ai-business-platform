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
