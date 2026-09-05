import type { UUID, Timestamped, UserBrief } from "@/types";

export type MeetingStatus =
  | "uploading"
  | "transcribing"
  | "analyzing"
  | "embedding"
  | "completed"
  | "failed";

export interface Meeting extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  title: string;
  recordedAt: string | null;
  durationSec: number | null;
  status: MeetingStatus;
  hasTranscript: boolean;
  hasSummary: boolean;
  actionItemCount: number;
  createdBy: UserBrief;
}

export interface MeetingSummary {
  summary: string;
  keyDecisions: string[];
  topics: string[];
}

export interface TranscriptSegment {
  speaker: string;
  startSec: number;
  endSec: number;
  text: string;
}

export interface MeetingDetail extends Meeting {
  transcript: TranscriptSegment[] | null;
  summary: MeetingSummary | null;
  errorMessage: string | null; // S28b BUG-MEETING-FAILED-UI: 실패 사유 노출
  // BE get_meeting_detail 이 돌려주는 연결 프로젝트(MeetingProjectLink, 접근 가능한 것만)
  projects: { id: UUID; title: string; status: string; visibility: string }[];
}

export interface MeetingStatusResponse {
  status: MeetingStatus;
  errorMessage: string | null;
}

export interface CreateMeetingRequest {
  title: string;
  fileKey: string;
  recordedAt?: string | null;
}

export interface CreateMeetingResponse {
  id: UUID;
  status: MeetingStatus;
  message: string;
}
