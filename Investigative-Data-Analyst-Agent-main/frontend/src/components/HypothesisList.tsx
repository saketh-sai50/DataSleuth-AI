import React from 'react';
import { Hypothesis } from '../types';

interface HypothesisListProps {
  hypotheses: Hypothesis[];
}

export const HypothesisList: React.FC<HypothesisListProps> = ({ hypotheses }) => {
  if (hypotheses.length === 0) return null;

  const getProbBadgeColor = (prob: string) => {
    switch (prob.toUpperCase()) {
      case 'HIGH':
        return 'bg-green-500/10 text-green-400 border border-green-500/20';
      case 'MEDIUM':
        return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20';
      case 'LOW':
        return 'bg-red-500/10 text-red-400 border border-red-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border border-slate-500/20';
    }
  };

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-white">Generated Hypotheses</h2>
        <p className="text-[10px] text-[#94a3b8]">Plausible business causes under investigation</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[300px] overflow-y-auto pr-1">
        {hypotheses.map((hyp) => (
          <div key={hyp.id} className="bg-[#141620] border border-[#2a2d3e] rounded-lg p-3.5 flex flex-col justify-between space-y-3">
            <div className="space-y-1.5">
              <div className="flex justify-between items-start gap-2">
                <h4 className="text-xs font-semibold text-white leading-snug">{hyp.title}</h4>
                <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${getProbBadgeColor(hyp.prior_probability)}`}>
                  {hyp.prior_probability}
                </span>
              </div>
              <p className="text-[11px] text-[#94a3b8] leading-relaxed">
                {hyp.description}
              </p>
            </div>

            <div className="border-t border-[#2a2d3e] pt-2 mt-1">
              <span className="text-[9px] text-[#64748b] font-semibold uppercase">Requirements</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {hyp.validation_data_needed.map((need, i) => (
                  <span
                    key={i}
                    className="text-[9px] bg-[#2a2d3e] text-[#e2e8f0] px-2 py-0.5 rounded font-mono truncate max-w-[150px]"
                    title={need}
                  >
                    {need}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
