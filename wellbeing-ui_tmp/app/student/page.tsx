"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type StudentInsights = {
  focus: number;        // 0..1
  stress: number;       // 0..1
  engagement: number;   // 0..1
  relaxation: number;   // 0..1
  signal_quality: "good" | "medium" | "poor";
};

export default function StudentDashboard() {
  const [data, setData] = useState<StudentInsights | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // keep a small trend for focus (last 40 points, ~80s at 2s interval)
  const focusTrendRef = useRef<number[]>([]);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8765";
    const url = `${base}/student/insights`;

    async function pull() {
      try {
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const json: StudentInsights = await res.json();
        setData(json);
        setErr(null);
        focusTrendRef.current = [...focusTrendRef.current, json.focus].slice(-40);
      } catch (e: any) {
        setErr(e?.message ?? "Fetch failed");
      }
    }

    pull();
    const id = setInterval(pull, 2000); // refresh every 2s
    return () => clearInterval(id);
  }, []);

  return (
    <main className="min-h-dvh bg-gradient-to-b from-slate-50 to-slate-100 p-6 md:p-10">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <header className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              Student Dashboard
            </h1>
            <p className="text-slate-600">Your real-time, private well-being view</p>
          </div>
          <SignalBadge quality={data?.signal_quality} />
        </header>

        {/* Error card */}
        {err && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
            <p className="font-semibold">Couldn’t fetch insights</p>
            <p className="text-sm">
              {err}. Ensure the mock backend is running at{" "}
              <code className="rounded bg-white/70 px-1">http://localhost:8765</code> and your{" "}
              <code className="rounded bg-white/70 px-1">.env.local</code> has{" "}
              <code className="rounded bg-white/70 px-1">NEXT_PUBLIC_API_URL</code>.
            </p>
          </div>
        )}

        {/* KPI donuts */}
        <section className="grid gap-6 md:grid-cols-4">
          <KpiDonut title="Focus" value={(data?.focus ?? 0) * 100} accent="indigo" subtitle="Task attention" />
          <KpiDonut title="Stress" value={(data?.stress ?? 0) * 100} accent="rose" subtitle="Physio arousal" />
          <KpiDonut title="Engagement" value={(data?.engagement ?? 0) * 100} accent="emerald" subtitle="Involvement" />
          <KpiDonut title="Relaxation" value={(data?.relaxation ?? 0) * 100} accent="cyan" subtitle="Calmness" />
        </section>

        {/* Trend + helper tips */}
        <section className="grid gap-6 md:grid-cols-3">
          {/* Focus trend (sparkline) */}
          <div className="md:col-span-2 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <div className="mb-2 flex items-baseline justify-between">
              <h3 className="text-lg font-semibold text-slate-900">Your Focus Trend</h3>
              <span className="text-sm text-slate-500">last {focusTrendRef.current.length} samples</span>
            </div>
            <Sparkline
              values={focusTrendRef.current}
              height={120}
              stroke="#6366f1" // indigo-500
              bg="#f8fafc"     // slate-50
            />
            <p className="mt-2 text-sm text-slate-600">
              Tip: brief posture reset + two slow breaths can nudge focus upward within a minute.
            </p>
          </div>

          {/* Gentle guidance card */}
          <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h3 className="text-lg font-semibold text-slate-900">Quick Tips</h3>
            <ul className="mt-2 space-y-2 text-sm text-slate-700">
              <li>• If stress spikes, try a 20-second box-breathing cycle.</li>
              <li>• Use short breaks to prevent focus dips (e.g., 25/5 min Pomodoro).</li>
              <li>• Poor signal? Adjust headband contact until the badge turns green.</li>
            </ul>
          </div>
        </section>

        {/* Debug JSON */}
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
function KpiDonut(props: { title: string; value: number; accent: "indigo" | "rose" | "emerald" | "cyan"; subtitle?: string }) {
  const { title, value, accent, subtitle } = props;
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  const color =
    accent === "indigo" ? "#6366f1" :
    accent === "rose"   ? "#fb7185" :
    accent === "emerald"? "#10b981" : "#06b6d4"; // cyan-500
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
          style={{ background: `conic-gradient(${color} ${pct}%, ${track} ${pct}% 100%)` }}
        >
          <div className="grid size-16 place-items-center rounded-full bg-white text-center">
            <span className="text-xl font-bold text-slate-900">{pct}%</span>
          </div>
        </div>
        {/* Legend */}
        <div className="space-y-2 text-sm">
          <Legend color={color} label="Current" value={`${pct}%`} />
          <Legend color={track} label="Remaining" value={`${100 - pct}%`} />
          <p className="text-xs text-slate-500">Local-only, anonymized metrics.</p>
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

/* ---------- Signal quality badge ---------- */
function SignalBadge({ quality }: { quality?: "good" | "medium" | "poor" }) {
  const q = quality ?? "poor";
  const color =
    q === "good" ? "bg-emerald-100 text-emerald-700 ring-emerald-200" :
    q === "medium" ? "bg-amber-100 text-amber-700 ring-amber-200" :
    "bg-rose-100 text-rose-700 ring-rose-200";
  const dot =
    q === "good" ? "bg-emerald-500" :
    q === "medium" ? "bg-amber-500" : "bg-rose-500";
  return (
    <span className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm ring-1 ${color}`}>
      <span className={`inline-block size-2.5 rounded-full ${dot}`}></span>
      Signal: <b className="font-semibold capitalize">{q}</b>
    </span>
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
  const width = Math.max(240, values.length * 10);
  const padded = values.length > 0 ? values : [0.5];

  const points = padded.map((v, i) => {
    const x = (i / Math.max(1, padded.length - 1)) * (width - 16) + 8;
    const y = (1 - clamp01(v)) * (height - 16) + 8; // invert Y (0 at bottom)
    return `${x},${y}`;
  });

  const area = `${points.join(" ")} ${width - 8},${height - 8} 8,${height - 8}`;

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="rounded-xl ring-1 ring-slate-200">
      <rect x="0" y="0" width={width} height={height} fill={bg} />
      <polyline fill={hexWithAlpha(stroke, 0.15)} stroke="none" points={area} />
      <polyline fill="none" stroke={stroke} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" points={points.join(" ")} />
    </svg>
  );
}

function clamp01(v: number) {
  return Math.max(0, Math.min(1, v));
}

function hexWithAlpha(hex: string, alpha: number) {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return hex;
  const r = parseInt(m[1], 16);
  const g = parseInt(m[2], 16);
  const b = parseInt(m[3], 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}