"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type InstructorSummary = {
  module: string;
  avg_focus: number;      // 0..1
  avg_stress: number;     // 0..1
  avg_engagement: number; // 0..1
  students_high_stress: number;
  students_total: number;
};

export default function InstructorDashboard() {
  const [data, setData] = useState<InstructorSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Keep short trend history for the sparkline (focus over time).
  const focusTrendRef = useRef<number[]>([]);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8765";
    const url  = `${base}/instructor/summary`;

    async function pull() {
      try {
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const json: InstructorSummary = await res.json();
        setData(json);
        setErr(null);

        // Update focus sparkline (last 30 points)
        focusTrendRef.current = [...focusTrendRef.current, json.avg_focus].slice(-30);
      } catch (e: any) {
        setErr(e?.message ?? "Fetch failed");
      }
    }

    pull();
    const id = setInterval(pull, 3000);  // refresh every 3s
    return () => clearInterval(id);
  }, []);

  // Derived values
  const hi = data?.students_high_stress ?? 0;
  const total = data?.students_total ?? 0;
  const hiPct = useMemo(() => Math.round((hi / Math.max(1, total)) * 100), [hi, total]);

  return (
    <main className="min-h-dvh bg-gradient-to-b from-slate-50 to-slate-100 p-6 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              Instructor Dashboard
            </h1>
            <p className="text-slate-600">Anonymous class well-being overview</p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-xl bg-white/70 px-3 py-2 shadow-sm ring-1 ring-slate-200 backdrop-blur">
            <span className="text-sm text-slate-600">Current Module:</span>
            <span className="rounded-lg bg-indigo-50 px-2 py-1 text-sm font-semibold text-indigo-700">
              {data?.module ?? "—"}
            </span>
          </div>
        </header>

        {/* Error card */}
        {err && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
            <p className="font-semibold">Couldn’t fetch summary</p>
            <p className="text-sm">
              {err}. Ensure the mock backend is running at{" "}
              <code className="rounded bg-white/70 px-1">http://localhost:8765</code> and your{" "}
              <code className="rounded bg-white/70 px-1">.env.local</code> has{" "}
              <code className="rounded bg-white/70 px-1">NEXT_PUBLIC_API_URL</code>.
            </p>
          </div>
        )}

        {/* KPI cards */}
        <section className="grid gap-6 md:grid-cols-3">
          <KpiDonut
            title="Average Focus"
            value={(data?.avg_focus ?? 0) * 100}
            accent="indigo"
            subtitle="Class attention level"
          />
          <KpiDonut
            title="Average Stress"
            value={(data?.avg_stress ?? 0) * 100}
            accent="rose"
            subtitle="Physiological arousal proxy"
          />
          <KpiDonut
            title="Average Engagement"
            value={(data?.avg_engagement ?? 0) * 100}
            accent="emerald"
            subtitle="Participation & involvement"
          />
        </section>

        {/* Trend + Stress distribution */}
        <section className="grid gap-6 md:grid-cols-3">
          {/* Focus trend (sparkline) */}
          <div className="md:col-span-2 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <div className="mb-2 flex items-baseline justify-between">
              <h3 className="text-lg font-semibold text-slate-900">Focus Trend (last 30 samples)</h3>
              <span className="text-sm text-slate-500">updates every 3s</span>
            </div>
            <Sparkline
              values={focusTrendRef.current}
              height={120}
              stroke="#6366f1" // indigo-500
              bg="#f8fafc"     // slate-50
            />
            <p className="mt-2 text-sm text-slate-600">
              Shows how average focus has changed over time during this session.
            </p>
          </div>

          {/* High-stress distribution */}
          <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h3 className="text-lg font-semibold text-slate-900">High-Stress Students</h3>
            <p className="text-sm text-slate-600">Current cohort under heightened stress</p>

            <div className="mt-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600">Count</span>
                <b className="text-slate-900">{hi} / {total} ({hiPct}%)</b>
              </div>
              <div className="mt-2 h-3 w-full rounded-full bg-slate-100">
                <div
                  className="h-3 rounded-full bg-rose-400 transition-[width] duration-500"
                  style={{ width: `${hiPct}%` }}
                />
              </div>
            </div>

            <ul className="mt-4 space-y-1 text-sm text-slate-600">
              <li>• Auto-excludes poor signal windows</li>
              <li>• Uses anonymized, derived metrics only</li>
              <li>• Intended for teaching strategy, not grading</li>
            </ul>
          </div>
        </section>

        {/* Raw JSON (debug) */}
        <details className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
          <summary className="cursor-pointer text-sm font-medium text-slate-700">Debug JSON</summary>
          <pre className="mt-3 overflow-auto rounded-lg bg-[#0b1020] p-3 text-[#9fe870]">
{JSON.stringify(data, null, 2)}
          </pre>
        </details>
      </div>
    </main>
  );
}

/* ---------- Pretty donut KPI (pure CSS via conic-gradient) ---------- */
function KpiDonut(props: { title: string; value: number; accent: "indigo" | "rose" | "emerald"; subtitle?: string }) {
  const { title, value, accent, subtitle } = props;
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  const color =
    accent === "indigo" ? "#6366f1" : accent === "rose" ? "#fb7185" : "#10b981"; // 500 shades
  const track = "#e5e7eb"; // slate-200

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        {subtitle && <span className="text-xs text-slate-500">{subtitle}</span>}
      </div>
      <div className="flex items-center gap-5">
        {/* Donut */}
        <div
          className="grid size-24 place-items-center rounded-full"
          style={{
            background: `conic-gradient(${color} ${pct}%, ${track} ${pct}% 100%)`,
          }}
        >
          <div className="grid size-16 place-items-center rounded-full bg-white text-center">
            <span className="text-xl font-bold text-slate-900">{pct}%</span>
          </div>
        </div>
        {/* Legend */}
        <div className="space-y-2 text-sm">
          <Legend color={color} label="Current" value={`${pct}%`} />
          <Legend color={track} label="Remaining" value={`${100 - pct}%`} />
          <p className="text-xs text-slate-500">
            Computed from anonymized, aggregated signals.
          </p>
        </div>
      </div>
    </div>
  );
}

function Legend({ color, label, value }: { color: string; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="inline-block size-3 rounded-[4px]" style={{ background: color }} />
      <span className="text-slate-700">{label}</span>
      <span className="ml-auto font-semibold text-slate-900">{value}</span>
    </div>
  );
}

/* ---------- Minimal sparkline (SVG, no libs) ---------- */
function Sparkline({
  values,
  height = 100,
  stroke = "#6366f1",
  bg = "#ffffff",
}: {
  values: number[];
  height?: number;
  stroke?: string;
  bg?: string;
}) {
  const width = Math.max(240, values.length * 10); // scale width with samples
  const padded = values.length > 0 ? values : [0.5]; // avoid empty path

  // Normalize 0..1 → pixel coords (y inverted)
  const points = padded.map((v, i) => {
    const x = (i / Math.max(1, padded.length - 1)) * (width - 16) + 8; // 8px padding
    const y = (1 - clamp01(v)) * (height - 16) + 8;
    return `${x},${y}`;
  });

  // Fill under the curve for a nicer look
  const area = `${points.join(" ")} ${width - 8},${height - 8} 8,${height - 8}`;

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="rounded-xl ring-1 ring-slate-200">
      <rect x="0" y="0" width={width} height={height} fill={bg} />
      <polyline
        fill={hexWithAlpha(stroke, 0.15)}
        stroke="none"
        points={area}
      />
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points.join(" ")}
      />
    </svg>
  );
}

function clamp01(v: number) {
  return Math.max(0, Math.min(1, v));
}

function hexWithAlpha(hex: string, alpha: number) {
  // Accepts #RRGGBB, returns rgba(...)
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return hex;
  const r = parseInt(m[1], 16);
  const g = parseInt(m[2], 16);
  const b = parseInt(m[3], 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
