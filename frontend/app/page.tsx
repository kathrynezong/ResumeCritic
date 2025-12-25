"use client";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export default function Home() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const [file, setFile] = useState<File | null>(null);
  const [jobText, setJobText] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !jobText) {
      alert("Please upload a resume and paste a job description!");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("resume", file);
    formData.append("job_text", jobText);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/analyze", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch (error) {
      alert("Error connecting to backend");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative min-h-screen p-8 bg-[var(--background)] text-[var(--text-main)] transition-colors">
      {/* 🌞 / 🌙 THEME TOGGLE BUTTON — place this ABOVE your content */}
      {mounted && (
        <button
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          className="absolute top-4 right-4 p-2 rounded-full bg-[var(--card)] shadow hover:shadow-md transition z-10"
          aria-label="Toggle theme"
        >
          {theme === "light" ? "🌙" : "☀️"}
        </button>
      )}

      {/* MAIN HEADER */}
      <h1 className="text-3xl font-bold text-center mb-2">ResumeCritic</h1>
      <p className="text-center text-sm text-[var(--text-muted)] mb-8">AI-Powered Semantic Analysis</p>

      {/* MAIN CONTENT - SIDE BY SIDE LAYOUT */}
      <div className="flex flex-col lg:flex-row gap-8 items-start justify-center max-w-7xl mx-auto">
        {/* LEFT SIDE - UPLOAD FORM */}
        <div className="w-full lg:w-1/2 lg:max-w-md">
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-4 bg-[var(--card)] p-6 rounded-2xl shadow-md sticky top-8"
          >
            <h2 className="text-xl font-semibold mb-2">Upload & Analyze</h2>
            <input
              type="file"
              accept=".pdf,.txt,.doc,.docx"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="border border-gray-300 text-[var(--text-main)] p-2 w-full rounded-md"
            />

            <textarea
              value={jobText}
              onChange={(e) => setJobText(e.target.value)}
              placeholder="Paste job description here..."
              className="border border-gray-300 text-[var(--text-main)] p-2 w-full h-96 rounded-md resize-y"
            />

            <button
              type="submit"
              disabled={loading}
              className="bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white px-4 py-2 rounded-md font-semibold disabled:opacity-50"
            >
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </form>
        </div>

        {/* RIGHT SIDE - RESULTS */}
        <div className="w-full lg:w-1/2 lg:max-w-2xl">
          {result ? (
            <div className="bg-[var(--card)] p-6 rounded-2xl shadow-md">
          <h2 className="text-xl font-bold mb-4">Analysis Results</h2>

          <div className="mb-4">
            <p className="text-[var(--text-muted)] mb-1">Overall Match Score</p>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="bg-[var(--accent)] h-3 rounded-full transition-all duration-500"
                style={{ width: `${result.match_score ?? 0}%` }}
              />
            </div>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              {result.match_score ?? 0}% overall match
            </p>
          </div>

          {/* Semantic and Keyword Scores */}
          {(result.semantic_score || result.keyword_score || result.gpt_analysis?.enabled) && (
            <div className="mb-4 grid grid-cols-3 gap-4">
              {result.semantic_score && (
                <div>
                  <p className="text-xs text-[var(--text-muted)] mb-1">Semantic</p>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${result.semantic_score}%` }}
                    />
                  </div>
                  <p className="text-xs text-[var(--text-muted)] mt-1">{result.semantic_score.toFixed(1)}%</p>
                </div>
              )}
              {result.keyword_score !== undefined && (
                <div>
                  <p className="text-xs text-[var(--text-muted)] mb-1">Keyword</p>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${result.keyword_score}%` }}
                    />
                  </div>
                  <p className="text-xs text-[var(--text-muted)] mt-1">{result.keyword_score}%</p>
                </div>
              )}
              {result.gpt_analysis?.enabled && (
                <div>
                  <p className="text-xs text-[var(--text-muted)] mb-1">Gemini AI</p>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${result.gpt_analysis.overall_score}%` }}
                    />
                  </div>
                  <p className="text-xs text-[var(--text-muted)] mt-1">{result.gpt_analysis.overall_score}%</p>
                </div>
              )}
            </div>
          )}

          {/* Gemini AI Analysis Summary */}
          {result.gpt_analysis?.enabled && (
            <div className="mb-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border-l-4 border-purple-500">
              <h3 className="font-semibold mb-3 text-base flex items-center gap-2">
                <span>🤖</span>
                <span>Gemini AI Analysis</span>
              </h3>
              
              {/* AI Summary - Prominently Displayed */}
              {result.gpt_analysis.summary && (
                <div className="mb-4 p-3 bg-white dark:bg-gray-800 rounded-md border border-purple-200 dark:border-purple-800">
                  <p className="text-sm font-medium mb-1 text-[var(--text-main)]">AI Summary:</p>
                  <p className="text-sm text-[var(--text-main)] leading-relaxed">{result.gpt_analysis.summary}</p>
                </div>
              )}
              
              {/* Recommendation Badge */}
              {result.gpt_analysis.recommendation && (
                <div className="mb-3">
                  <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-purple-200 dark:bg-purple-800 text-purple-800 dark:text-purple-200">
                    Recommendation: {result.gpt_analysis.recommendation?.replace(/_/g, ' ')}
                  </span>
                </div>
              )}
              
              {/* Detailed Scores */}
              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">Technical Skills:</span>
                  <span className="font-semibold">{result.gpt_analysis.technical_skills}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">Experience:</span>
                  <span className="font-semibold">{result.gpt_analysis.experience_level}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">Education:</span>
                  <span className="font-semibold">{result.gpt_analysis.education}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-muted)]">Domain Knowledge:</span>
                  <span className="font-semibold">{result.gpt_analysis.domain_knowledge}%</span>
                </div>
              </div>
              
              {/* Strengths and Gaps */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {result.gpt_analysis.strengths?.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold mb-1 text-green-700 dark:text-green-400">✅ Strengths:</p>
                    <ul className="text-xs list-disc list-inside text-[var(--text-muted)] space-y-1">
                      {result.gpt_analysis.strengths.map((s: string, i: number) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {result.gpt_analysis.gaps?.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold mb-1 text-red-700 dark:text-red-400">⚠️ Areas to Improve:</p>
                    <ul className="text-xs list-disc list-inside text-[var(--text-muted)] space-y-1">
                      {result.gpt_analysis.gaps.map((g: string, i: number) => (
                        <li key={i}>{g}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          <div>
            <p className="text-[var(--text-muted)] mb-2 font-medium">
              Missing Keywords
            </p>
            {result.missing_keywords?.length ? (
              <div className="flex flex-wrap gap-2">
                {result.missing_keywords.map((kw: string, i: number) => (
                  <span
                    key={i}
                    className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs font-medium"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-muted)]">
                No missing keywords 🎉
              </p>
            )}
          </div>
          {result.matched_keywords && result.matched_keywords.length > 0 && (
            <div className="mb-4">
              <p className="text-[var(--text-muted)] mb-2 font-medium">
                Matched Keywords
              </p>
              <div className="flex flex-wrap gap-2">
                {result.matched_keywords.map((kw: string, i: number) => (
                  <span
                    key={i}
                    className="bg-green-100 text-green-700 px-2 py-1 rounded-full text-xs font-medium"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="mb-4">
            <p className="text-[var(--text-muted)] mb-2 font-medium">
              Resume Keywords
            </p>
            {result.resume_keywords?.length ? (
              <div className="flex flex-wrap gap-2">
                {result.resume_keywords.map((kw: string, i: number) => (
                  <span
                    key={i}
                    className="bg-purple-100 text-purple-700 px-2 py-1 rounded-full text-xs font-medium"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-muted)]">
                No resume keywords detected.
              </p>
            )}
          </div>
          <div>
            <p className="text-[var(--text-muted)] mb-2 font-medium">
              Job Posting Keywords
            </p>
            {result.job_keywords?.length ? (
              <div className="flex flex-wrap gap-2">
                {result.job_keywords.map((kw: string, i: number) => (
                  <span
                    key={i}
                    className="bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-xs font-medium"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[var(--text-muted)]">
                No job keywords detected.
              </p>
            )}
          </div>
            </div>
          ) : (
            <div className="bg-[var(--card)] p-6 rounded-2xl shadow-md text-center text-[var(--text-muted)]">
              <p>Upload a resume and job description to see AI-powered semantic analysis.</p>
              <p className="text-xs mt-2">Uses advanced NLP to understand meaning beyond keywords</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
