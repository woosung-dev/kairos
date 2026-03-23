import type { UUID, Timestamped, UserBrief } from "@/types";

export type MeetingStatus =
  | "uploading"
  | "transcribing"
  | "summarizing"
  | "completed"
  | "failed";

export interface Meeting extends Timestamped {
  id: UUID;
  workspaceId: UUID;
  paraItemId: UUID | null;
  title: string;
  recordedAt: string | null;
  durationSec: number | null;
  status: MeetingStatus;
  hasTranscript: boolean;
  hasSummary: boolean;
  actionItemCount: number;
  createdBy: UserBrief;
}

export interface TranscriptSegment {
  speaker: string;
  startSec: number;
  endSec: number;
  text: string;
}

export interface MeetingSummary {
  summary: string;
  keyDecisions: string[];
  topics: string[];
}

export interface MeetingDetail extends Meeting {
  transcript: TranscriptSegment[] | null;
  summary: MeetingSummary | null;
}
