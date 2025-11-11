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
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-8 p-8 bg-[var(--background)] text-[var(--text-main)] transition-colors">
      {/* 🌞 / 🌙 THEME TOGGLE BUTTON — place this ABOVE your content */}
      {mounted && (
        <button
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          className="absolute top-4 right-4 p-2 rounded-full bg-[var(--card)] shadow hover:shadow-md transition"
          aria-label="Toggle theme"
        >
          {theme === "light" ? "🌙" : "☀️"}
        </button>
      )}

      {/* MAIN HEADER */}
      <h1 className="text-3xl font-bold">ResumeCritic</h1>

      {/* UPLOAD FORM */}
      <form
        onSubmit={handleSubmit}
        className="flex flex-col items-center gap-4 bg-[var(--card)] p-6 rounded-2xl shadow-md w-full max-w-md"
      >
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
          className="border border-gray-300 text-[var(--text-main)] p-2 w-full h-32 rounded-md"
        />

        <button
          type="submit"
          disabled={loading}
          className="bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white px-4 py-2 rounded-md font-semibold disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </form>

      {/* RESULTS */}
      {result && (
        <div className="mt-8 bg-[var(--card)] p-6 rounded-2xl shadow-md w-full max-w-lg">
          <h2 className="text-xl font-bold mb-4">Analysis Results</h2>

          <div className="mb-4">
            <p className="text-[var(--text-muted)] mb-1">Match Score</p>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div
                className="bg-[var(--accent)] h-3 rounded-full transition-all duration-500"
                style={{ width: `${result.match_score ?? 0}%` }}
              />
            </div>
            <p className="text-sm text-[var(--text-muted)] mt-1">
              {result.match_score ?? 0}% match
            </p>
          </div>

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
        </div>
      )}
    </main>
  );
}
