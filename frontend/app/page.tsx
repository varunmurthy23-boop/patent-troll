"use client";

import { AlertTriangle, FileSearch, Lightbulb, Loader2, RefreshCw, Scale, ShieldCheck } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { EndToEndResponse, IdeaPayload, runEndToEnd } from "../lib/api";

const disclaimer =
  "Not legal advice. This tool is a drafting and research aid only, does not represent users before the USPTO, does not submit filings, and does not guarantee patentability or grant. Review by a registered USPTO patent attorney or agent is strongly recommended before filing.";

const initialIdea: IdeaPayload = {
  title: "Adaptive code review risk router",
  problem:
    "Engineering teams waste reviewer time because pull requests are routed using static ownership rules that miss implementation risk.",
  mechanism:
    "The system builds a typed dependency graph from changed files, runtime incidents, code owners, and test coverage, then routes review requests based on graph paths affected by the change.",
  data_flow:
    "A pull request event enters an ingestion queue, changed files are mapped to graph nodes, incident and coverage signals update edge weights, and a ranked reviewer plan is written back to the code hosting system.",
  algorithm:
    "For each changed node, the algorithm performs bounded graph expansion, applies decayed incident weights and coverage penalties, computes reviewer expertise scores, and selects a minimal reviewer set that covers high-risk paths.",
  technical_novelty:
    "The graph edge weights are updated from production incident proximity and test coverage deltas so the routing decision reflects current runtime risk instead of static ownership alone.",
  implementation_notes:
    "The implementation uses a persistent graph index, webhook ingestion, and incremental recomputation to keep latency below two seconds for typical pull requests."
};

export default function Home() {
  const [idea, setIdea] = useState<IdeaPayload>(initialIdea);
  const [result, setResult] = useState<EndToEndResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const sourceMode = useMemo(() => {
    if (!result) return "";
    const providerError = result.search_metadata?.providers.find((provider) => provider.status === "error");
    if (providerError) {
      return `${providerError.provider} failed: ${providerError.message} Demo fallback results may be shown.`;
    }
    if (result.search_metadata?.demo_fallback_used) {
      return "Demo fallback results: add USPTO_ODP_API_KEY for live search.";
    }
    return "Live prior art search results.";
  }, [result]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await runEndToEnd(idea);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <div className="topbar">
        <div className="brand">
          <Scale size={24} aria-hidden="true" />
          <span>Patent Troll</span>
        </div>
        <div className="phase">Phase 1 MVP</div>
      </div>

      <section className="notice">
        <AlertTriangle size={20} aria-hidden="true" />
        <p>{disclaimer}</p>
      </section>

      <div className="workspace">
        <form className="panel intake" onSubmit={onSubmit}>
          <div className="section-title">
            <Lightbulb size={20} aria-hidden="true" />
            <div>
              <h1>Idea Intake</h1>
              <p>Capture the mechanism, data flow, and technical novelty before searching.</p>
            </div>
          </div>

          <Field label="Title" value={idea.title} onChange={(value) => setIdea({ ...idea, title: value })} />
          <Field
            label="Technical problem"
            value={idea.problem}
            onChange={(value) => setIdea({ ...idea, problem: value })}
            textarea
          />
          <Field
            label="Mechanism"
            value={idea.mechanism}
            onChange={(value) => setIdea({ ...idea, mechanism: value })}
            textarea
          />
          <Field
            label="Data flow"
            value={idea.data_flow}
            onChange={(value) => setIdea({ ...idea, data_flow: value })}
            textarea
          />
          <Field
            label="Algorithm"
            value={idea.algorithm}
            onChange={(value) => setIdea({ ...idea, algorithm: value })}
            textarea
          />
          <Field
            label="Technical novelty"
            value={idea.technical_novelty}
            onChange={(value) => setIdea({ ...idea, technical_novelty: value })}
            textarea
          />
          <Field
            label="Implementation notes"
            value={idea.implementation_notes}
            onChange={(value) => setIdea({ ...idea, implementation_notes: value })}
            textarea
          />

          {error ? <div className="error">{error}</div> : null}

          <button className="primary" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <RefreshCw size={18} aria-hidden="true" />}
            {loading ? "Running search and analysis" : "Run prior art and analysis"}
          </button>
        </form>

        <section className="results">
          <div className="panel">
            <div className="section-title">
              <FileSearch size={20} aria-hidden="true" />
              <div>
                <h2>Prior Art</h2>
                <p>{result ? sourceMode : "Results appear after the first run."}</p>
              </div>
            </div>
            <div className="result-list">
              {result?.prior_art.map((item) => (
                <article className="prior-art" key={item.id}>
                  <div className="result-meta">
                    <span>{item.source}</span>
                    <strong>{Math.round(item.similarity_score * 100)}%</strong>
                  </div>
                  <h3>{item.title}</h3>
                  <p>{item.abstract}</p>
                  <div className="reference">
                    <span>{item.external_id}</span>
                    {item.link ? (
                      <a href={item.link} target="_blank" rel="noreferrer">
                        Open reference
                      </a>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="panel">
            <div className="section-title">
              <ShieldCheck size={20} aria-hidden="true" />
              <div>
                <h2>Patentability Analysis</h2>
                <p>{result ? `Generated by ${result.analysis.generated_by}.` : "Novelty, obviousness, and eligibility are scored separately."}</p>
              </div>
            </div>

            {result ? (
              <>
                <div className="score-grid">
                  <Score label="Novelty" value={result.analysis.novelty_score} mode="positive" />
                  <Score label="Obviousness risk" value={result.analysis.obviousness_risk} mode="risk" />
                  <Score label="Section 101 risk" value={result.analysis.eligibility_risk} mode="risk" />
                </div>
                <p className="summary">{result.analysis.summary}</p>
                <ReportList title="Closest overlaps" items={result.analysis.overlaps} />
                <ReportList title="Section 101 flags" items={result.analysis.section_101_flags} />
                <ReportList title="Suggested technical tweaks" items={result.analysis.suggested_tweaks} />
                <footer className="report-footer">Drafted with AI assistance — review by a registered USPTO patent attorney or agent is strongly recommended before filing.</footer>
              </>
            ) : (
              <div className="empty-state">Run the first slice to create an analysis report.</div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

function Field({
  label,
  value,
  onChange,
  textarea = false
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  textarea?: boolean;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {textarea ? (
        <textarea value={value} onChange={(event) => onChange(event.target.value)} rows={4} required />
      ) : (
        <input value={value} onChange={(event) => onChange(event.target.value)} required />
      )}
    </label>
  );
}

function Score({ label, value, mode }: { label: string; value: number; mode: "positive" | "risk" }) {
  const width = `${Math.max(0, Math.min(100, value))}%`;
  return (
    <div className="score-card">
      <div className="score-label">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="score-track">
        <div className={mode === "positive" ? "score-fill positive" : "score-fill risk"} style={{ width }} />
      </div>
    </div>
  );
}

function ReportList({ title, items }: { title: string; items: Array<Record<string, string>> }) {
  return (
    <div className="report-list">
      <h3>{title}</h3>
      {items.map((item, index) => (
        <article key={`${title}-${index}`}>
          <strong>{item.title || item.flag || item.reference_id || "Item"}</strong>
          <p>{item.detail || item.overlap || item.risk || item.source || ""}</p>
        </article>
      ))}
    </div>
  );
}
