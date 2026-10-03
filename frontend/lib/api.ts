export type IdeaPayload = {
  title: string;
  problem: string;
  mechanism: string;
  data_flow: string;
  algorithm: string;
  technical_novelty: string;
  implementation_notes: string;
};

export type PriorArt = {
  id: string;
  source: string;
  external_id: string;
  title: string;
  abstract: string;
  publication_date: string;
  assignee: string;
  link: string;
  similarity_score: number;
};

export type AnalysisReport = {
  id: string;
  novelty_score: number;
  obviousness_risk: number;
  eligibility_risk: number;
  summary: string;
  overlaps: Array<Record<string, string>>;
  section_101_flags: Array<Record<string, string>>;
  suggested_tweaks: Array<Record<string, string>>;
  generated_by: string;
  disclaimer: string;
  created_at: string;
};

export type SearchMetadata = {
  query: string;
  demo_fallback_used: boolean;
  requested_limit: number;
  returned_count: number;
  providers: Array<{
    provider: string;
    status: string;
    result_count: number;
    message: string;
  }>;
};

export type EndToEndResponse = {
  idea: IdeaPayload & { id: string; status: string; created_at: string; updated_at: string };
  prior_art: PriorArt[];
  search_metadata: SearchMetadata | null;
  analysis: AnalysisReport;
  disclaimer: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function runEndToEnd(payload: IdeaPayload): Promise<EndToEndResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ideas/end-to-end`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Request failed with ${response.status}`);
  }

  return response.json();
}
