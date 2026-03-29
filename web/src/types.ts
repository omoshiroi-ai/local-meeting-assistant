export type SessionOut = {
  id: number;
  title: string;
  source: string;
  started_at: string;
  ended_at: string | null;
  duration_secs: number | null;
  notes: string;
  session_type: string;
  department_id: number | null;
  metadata: Record<string, unknown> | null;
  wbs_node_id: number | null;
  case_id: string | null;
  created_at: string;
  updated_at: string;
};

export type HealthSnapshot = {
  microphone: { ok: boolean; message: string };
  whisper: { ok: boolean; message: string };
  embedding: { ok: boolean; message: string };
  llm: { ok: boolean; message: string };
};

export type SegmentOut = {
  id: number;
  meeting_id: number;
  sequence_num: number;
  text: string;
  start_ms: number;
  end_ms: number;
  speaker_label: string | null;
  confidence: number | null;
  created_at: string;
};

export type ModelsResponse = {
  llm: { active_id: string; role: string; environment_default?: string };
  whisper: { active_id: string };
  embedding: { active_id: string };
  note: string;
};

export type LlmSettingsOut = {
  effective_model_id: string;
  effective_max_new_tokens: number;
  stored_model_id: string | null;
  stored_max_new_tokens: number | null;
  environment_model_id: string;
  environment_max_new_tokens: number;
};

export type RetrievalChunkOut = {
  id: number;
  chunk_index: number;
  text: string;
  start_ms: number;
  end_ms: number;
};

export type RetrievalPayload = {
  query: string;
  chunks: RetrievalChunkOut[];
  llm_model: string;
};
