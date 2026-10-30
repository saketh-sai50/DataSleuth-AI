import React from 'react';
import { Report } from '../types';

interface ReportViewerProps {
  report: Report | null;
}

const CHART_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#a855f7', '#06b6d4', '#f43f5e', '#84cc16'];

export const ReportViewer: React.FC<ReportViewerProps> = ({ report }) => {
  if (!report) return null;

  const getConfidenceColor = (score: number) => {
    if (score >= 0.75) return 'text-[#10b981]';
    if (score >= 0.5) return 'text-[#f59e0b]';
    return 'text-[#ef4444]';
  };

  const getConfidenceBg = (score: number) => {
    if (score >= 0.75) return 'bg-[#10b981]';
    if (score >= 0.5) return 'bg-[#f59e0b]';
    return 'bg-[#ef4444]';
  };

  // ── Pie / Donut Chart ──────────────────────────────────────────────────────
  const renderPieChart = (data: any, title: string, idx: number) => {
    const labels: string[] = data?.labels || [];
    const values: number[] = data?.values || [];
    if (!labels.length || !values.length) return null;

    const total = values.reduce((s, v) => s + v, 0) || 1;
    let cumulativePct = 0;
    const slices = labels.map((label, i) => {
      const val = values[i];
      const pct = (val / total) * 100;
      const start = cumulativePct;
      cumulativePct += pct;
      return { label, val, pct, start, end: cumulativePct };
    });

    const gradientStr = slices
      .map((s, i) => `${CHART_COLORS[i % CHART_COLORS.length]} ${s.start.toFixed(1)}% ${s.end.toFixed(1)}%`)
      .join(', ');

    return (
      <div key={idx} className="bg-[#141620] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
        <div className="flex items-center space-x-2 border-b border-[#2a2d3e] pb-3">
          <div className="w-1 h-4 bg-[#6366f1] rounded-full" />
          <h4 className="text-sm font-bold text-white">{title}</h4>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-6">
          {/* Donut */}
          <div
            className="relative w-36 h-36 rounded-full flex-shrink-0"
            style={{ background: `conic-gradient(${gradientStr})` }}
          >
            <div className="absolute inset-9 bg-[#141620] rounded-full border-2 border-[#2a2d3e] flex flex-col items-center justify-center">
              <span className="text-[10px] text-[#64748b] font-semibold uppercase tracking-wider">Total</span>
              <span className="text-xs font-bold text-white">
                {total >= 1_000_000
                  ? `${(total / 1_000_000).toFixed(1)}M`
                  : total >= 1_000
                  ? `${(total / 1_000).toFixed(1)}K`
                  : total.toFixed(0)}
              </span>
            </div>
          </div>

          {/* Legend */}
          <div className="flex-1 space-y-2 w-full">
            {slices.map((slice, i) => {
              const color = CHART_COLORS[i % CHART_COLORS.length];
              const barWidth = Math.max(4, slice.pct);
              return (
                <div key={i} className="space-y-0.5">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                      <span className="text-[#94a3b8] font-medium truncate max-w-[110px]">{slice.label}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-white">{slice.pct.toFixed(1)}%</span>
                      <span className="text-[#64748b] text-[10px]">({slice.val.toLocaleString()})</span>
                    </div>
                  </div>
                  <div className="w-full bg-[#2a2d3e] h-1.5 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${barWidth}%`, backgroundColor: color }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  // ── Bar Chart ─────────────────────────────────────────────────────────────
  const renderBarChart = (data: any, title: string, idx: number) => {
    const x: string[] = data?.x || [];
    const y: number[] = data?.y || [];
    if (!x.length || !y.length) return null;
    const maxVal = Math.max(...y) || 1;

    return (
      <div key={idx} className="bg-[#141620] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
        <div className="flex items-center space-x-2 border-b border-[#2a2d3e] pb-3">
          <div className="w-1 h-4 bg-[#10b981] rounded-full" />
          <h4 className="text-sm font-bold text-white">{title}</h4>
        </div>
        <div className="space-y-2.5">
          {x.map((label, i) => {
            const val = y[i];
            const pct = Math.max(4, (val / maxVal) * 100);
            const color = CHART_COLORS[i % CHART_COLORS.length];
            return (
              <div key={i} className="flex items-center space-x-3 text-xs group">
                <span className="w-20 text-[#94a3b8] truncate font-medium flex-shrink-0">{label}</span>
                <div className="flex-1 bg-[#2a2d3e] h-6 rounded-lg overflow-hidden relative">
                  <div
                    className="h-full rounded-lg transition-all duration-700"
                    style={{ width: `${pct}%`, backgroundColor: color, opacity: 0.85 }}
                  />
                  <span className="absolute left-2.5 top-1 text-[11px] font-bold text-white z-10">
                    {typeof val === 'number'
                      ? val >= 1_000_000
                        ? `${(val / 1_000_000).toFixed(2)}M`
                        : val >= 1_000
                        ? `${(val / 1_000).toFixed(1)}K`
                        : val.toLocaleString(undefined, { maximumFractionDigits: 1 })
                      : val}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // ── Line / Area Sparkline ─────────────────────────────────────────────────
  const renderLineChart = (data: any, title: string, idx: number) => {
    const x: string[] = data?.x || [];
    const y: number[] = data?.y || [];
    if (!x.length || !y.length) return null;
    const maxVal = Math.max(...y) || 1;

    return (
      <div key={idx} className="bg-[#141620] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
        <div className="flex items-center space-x-2 border-b border-[#2a2d3e] pb-3">
          <div className="w-1 h-4 bg-[#f59e0b] rounded-full" />
          <h4 className="text-sm font-bold text-white">{title}</h4>
        </div>
        <div className="h-32 flex items-end justify-between gap-0.5 px-1">
          {y.map((val, i) => {
            const heightPct = Math.max(6, (val / maxVal) * 100);
            return (
              <div key={i} className="flex-1 flex flex-col items-center justify-end h-full group">
                <div className="relative w-full flex justify-center">
                  <span className="absolute -top-5 opacity-0 group-hover:opacity-100 bg-[#2a2d3e] text-[9px] text-white px-1.5 py-0.5 rounded font-mono transition-opacity z-20 whitespace-nowrap">
                    {val.toLocaleString()}
                  </span>
                  <div
                    className="w-3/4 bg-gradient-to-t from-[#6366f1] to-[#818cf8] rounded-t-sm group-hover:from-[#4f46e5] transition-all duration-300"
                    style={{ height: `${heightPct}%` }}
                  />
                </div>
                {x[i] && (
                  <span className="text-[8px] text-[#475569] mt-1 font-mono truncate w-full text-center">
                    {x[i]}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // ── Dispatch chart type ───────────────────────────────────────────────────
  const renderChart = (chartConfig: any, idx: number) => {
    try {
      const data = chartConfig?.data?.[0];
      const title = chartConfig?.layout?.title?.text || `Chart ${idx + 1}`;
      const type: string = data?.type || 'bar';

      if (type === 'pie') return renderPieChart(data, title, idx);
      if (type === 'scatter' || type === 'line') return renderLineChart(data, title, idx);
      return renderBarChart(data, title, idx);
    } catch {
      return null;
    }
  };

  const hasCharts = report.charts && report.charts.length > 0;

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl overflow-hidden">

      {/* ── PowerBI-style header strip ───────────────────────────────────── */}
      <div className="bg-gradient-to-r from-[#6366f1]/10 via-[#1a1d27] to-[#10b981]/10 border-b border-[#2a2d3e] px-6 py-5 flex flex-col md:flex-row md:justify-between md:items-center gap-4">
        <div className="flex items-center space-x-3">
          <div className="bg-[#6366f1] p-2.5 rounded-lg shadow-lg shadow-[#6366f1]/20">
            <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Executive Business Report</h2>
            <p className="text-[11px] text-[#64748b]">AI-powered data analysis · PowerBI-style visualisations</p>
          </div>
        </div>

        {/* KPI chips */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="bg-[#141620] border border-[#2a2d3e] rounded-lg px-4 py-2 text-center">
            <p className="text-[9px] text-[#64748b] uppercase font-semibold">Confidence</p>
            <p className={`text-lg font-bold ${getConfidenceColor(report.overall_confidence)}`}>
              {(report.overall_confidence * 100).toFixed(0)}%
            </p>
          </div>
          <div className="bg-[#141620] border border-[#2a2d3e] rounded-lg px-4 py-2 text-center">
            <p className="text-[9px] text-[#64748b] uppercase font-semibold">Root Causes</p>
            <p className="text-lg font-bold text-[#6366f1]">{report.root_causes.length}</p>
          </div>
          <div className="bg-[#141620] border border-[#2a2d3e] rounded-lg px-4 py-2 text-center">
            <p className="text-[9px] text-[#64748b] uppercase font-semibold">Charts</p>
            <p className="text-lg font-bold text-[#f59e0b]">{report.charts?.length || 0}</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">

        {/* ── Executive Summary ──────────────────────────────────────────── */}
        <div className="bg-[#6366f1]/5 border border-[#6366f1]/20 rounded-xl p-5">
          <p className="text-[10px] uppercase font-bold text-[#6366f1] tracking-widest mb-2">📋 Executive Summary</p>
          <p className="text-sm text-[#e2e8f0] font-medium leading-relaxed">{report.executive_summary}</p>
        </div>

        {/* ── Charts Grid (full-width, PowerBI-style) ────────────────────── */}
        {hasCharts && (
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-1 h-5 bg-gradient-to-b from-[#6366f1] to-[#10b981] rounded-full" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">📊 Visual Analytics</h3>
              <span className="text-[10px] bg-[#6366f1]/10 text-[#6366f1] border border-[#6366f1]/20 px-2 py-0.5 rounded-full font-semibold">
                {report.charts.length} chart{report.charts.length !== 1 ? 's' : ''}
              </span>
            </div>
            <div className={`grid gap-4 ${report.charts.length === 1 ? 'grid-cols-1' : 'grid-cols-1 lg:grid-cols-2'}`}>
              {report.charts.map((config, idx) => renderChart(config, idx))}
            </div>
          </div>
        )}

        {/* ── Root Causes + Recommendations + Evidence grid ──────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Left: Root Causes */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-1 h-5 bg-[#ef4444] rounded-full" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">🔍 Root Causes</h3>
            </div>
            {report.root_causes.map((rc, idx) => (
              <div key={idx} className="bg-[#141620] border border-[#2a2d3e] rounded-lg p-3.5 space-y-2">
                <div className="flex justify-between items-start gap-2">
                  <span className="text-xs font-semibold text-white leading-snug">{rc.cause}</span>
                  <span className={`flex-shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    rc.confidence >= 0.75 ? 'bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20' :
                    rc.confidence >= 0.5 ? 'bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/20' :
                    'bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/20'
                  }`}>
                    {(rc.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-[11px] text-[#64748b] leading-relaxed">
                  <span className="text-[#94a3b8] font-semibold">Evidence: </span>{rc.evidence}
                </p>
              </div>
            ))}
          </div>

          {/* Right: Recommendations + Evidence */}
          <div className="space-y-6">
            {/* Recommendations */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <div className="w-1 h-5 bg-[#6366f1] rounded-full" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">💡 Recommendations</h3>
              </div>
              <ul className="space-y-2">
                {report.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start space-x-2.5 bg-[#141620] border border-[#2a2d3e] rounded-lg p-3 text-xs text-[#e2e8f0]">
                    <span className="flex-shrink-0 text-[#6366f1] bg-[#6366f1]/10 w-5 h-5 rounded-full flex items-center justify-center font-bold text-[10px] mt-0.5">
                      {idx + 1}
                    </span>
                    <span className="leading-relaxed">{rec}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Evidence */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <div className="w-1 h-5 bg-[#10b981] rounded-full" />
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">✅ Data Evidence</h3>
              </div>
              <ul className="space-y-2">
                {report.evidence.map((ev, idx) => (
                  <li key={idx} className="flex items-start space-x-2.5 text-xs text-[#e2e8f0]">
                    <span className="text-[#10b981] bg-[#10b981]/10 p-1 rounded mt-0.5 flex-shrink-0">
                      <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </span>
                    <span className="leading-relaxed text-[#94a3b8]">{ev}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* ── Next Steps ─────────────────────────────────────────────────── */}
        {report.next_steps.length > 0 && (
          <div className="border-t border-[#2a2d3e] pt-5 space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-1 h-5 bg-[#f59e0b] rounded-full" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">🚀 Next Action Steps</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {report.next_steps.map((step, idx) => (
                <div key={idx} className="flex items-center space-x-3 bg-[#141620] border border-[#2a2d3e] rounded-lg p-3 text-xs text-[#e2e8f0]">
                  <span className="font-mono text-[#f59e0b] font-bold bg-[#f59e0b]/10 border border-[#f59e0b]/20 px-2 py-0.5 rounded flex-shrink-0">
                    0{idx + 1}
                  </span>
                  <span className="leading-relaxed">{step}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Limitations ────────────────────────────────────────────────── */}
        {report.limitations.length > 0 && (
          <div className="border-t border-[#2a2d3e] pt-5 space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-1 h-5 bg-[#ef4444] rounded-full" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">⚠️ Limitations & Gaps</h3>
            </div>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {report.limitations.map((lim, idx) => (
                <li key={idx} className="flex items-start space-x-2 text-xs text-[#94a3b8] bg-[#141620] border border-[#2a2d3e] rounded-lg p-2.5">
                  <span className="text-[#ef4444] flex-shrink-0 mt-0.5">⚠</span>
                  <span className="leading-relaxed">{lim}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
