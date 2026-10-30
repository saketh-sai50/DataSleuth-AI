import React from 'react';
import { Investigation } from '../types';

interface InvestigationTimelineProps {
  investigation: Investigation | null;
}

export const InvestigationTimeline: React.FC<InvestigationTimelineProps> = ({
  investigation,
}) => {
  if (!investigation) return null;

  const steps = [
    { key: 'initiated', label: 'Initiated' },
    { key: 'analyzing', label: 'Analyzing Data' },
    { key: 'waiting_for_data', label: 'Data Requested' },
    { key: 'completed', label: 'Report Ready' },
  ];

  const getStepStatus = (stepKey: string) => {
    const currentStatus = investigation.status.toLowerCase();
    
    if (currentStatus === 'completed') return 'completed';
    if (currentStatus === 'failed') return 'failed';

    const statusOrder = ['initiated', 'analyzing', 'waiting_for_data', 'generating_report', 'completed'];
    const currentIndex = statusOrder.indexOf(currentStatus);
    const stepIndex = statusOrder.indexOf(stepKey);

    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-white">Investigation Status</h2>
        <p className="text-[10px] text-[#94a3b8]">Real-time execution pipeline timeline</p>
      </div>

      <div className="relative flex items-center justify-between">
        {/* Horizontal Line Connecting Steps */}
        <div className="absolute left-4 right-4 h-0.5 bg-[#2a2d3e] top-3.5 -z-0"></div>

        {steps.map((step) => {
          const status = getStepStatus(step.key);
          
          let circleBg = 'bg-[#141620] border-[#2a2d3e] text-[#64748b]';
          let textColor = 'text-[#64748b]';

          if (status === 'completed') {
            circleBg = 'bg-[#10b981] border-[#10b981] text-white';
            textColor = 'text-[#10b981] font-medium';
          } else if (status === 'active') {
            circleBg = 'bg-[#6366f1] border-[#6366f1] text-white ring-4 ring-[#6366f1]/20';
            textColor = 'text-white font-medium';
          }

          return (
            <div key={step.key} className="flex flex-col items-center z-10 space-y-2 flex-1">
              <div className={`h-7.5 w-7.5 rounded-full flex items-center justify-center text-xs border-2 font-bold ${circleBg}`}>
                {status === 'completed' ? (
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <span>{steps.indexOf(step) + 1}</span>
                )}
              </div>
              <span className={`text-[10px] text-center ${textColor}`}>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      <div className="border-t border-[#2a2d3e] pt-3 mt-1 flex justify-around text-center text-xs">
        <div>
          <p className="text-[#64748b] text-[9px] uppercase font-semibold">Hypotheses</p>
          <p className="text-white font-semibold mt-0.5">{investigation.hypotheses.length}</p>
        </div>
        <div className="border-l border-[#2a2d3e]"></div>
        <div>
          <p className="text-[#64748b] text-[9px] uppercase font-semibold">Missing Datasets</p>
          <p className="text-white font-semibold mt-0.5">{investigation.missing_datasets.length}</p>
        </div>
        <div className="border-l border-[#2a2d3e]"></div>
        <div>
          <p className="text-[#64748b] text-[9px] uppercase font-semibold">Session ID</p>
          <p className="text-white font-mono mt-0.5">#{investigation.id}</p>
        </div>
      </div>
    </div>
  );
};
