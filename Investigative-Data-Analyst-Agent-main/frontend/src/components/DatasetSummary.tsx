import React from 'react';
import { Dataset } from '../types';

interface DatasetSummaryProps {
  datasets: Dataset[];
  selectedDatasetIds: number[];
}

export const DatasetSummary: React.FC<DatasetSummaryProps> = ({
  datasets,
  selectedDatasetIds,
}) => {
  const activeDatasets = datasets.filter((ds) => selectedDatasetIds.includes(ds.id));

  if (activeDatasets.length === 0) {
    return null;
  }

  const getTypeBadgeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'numeric':
        return 'bg-blue-500/10 text-blue-400 border border-blue-500/20';
      case 'categorical':
        return 'bg-green-500/10 text-green-400 border border-green-500/20';
      case 'datetime':
        return 'bg-purple-500/10 text-purple-400 border border-purple-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border border-slate-500/20';
    }
  };

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-white">Active Schemas</h2>
        <p className="text-[10px] text-[#94a3b8]">In-memory structures of selected datasets</p>
      </div>

      <div className="space-y-5">
        {activeDatasets.map((ds) => (
          <div key={ds.id} className="border-t border-[#2a2d3e] pt-4 first:border-0 first:pt-0">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-semibold text-white">{ds.filename}</span>
              <span className="text-[10px] text-[#64748b] font-medium">
                {ds.row_count} rows × {ds.column_count} cols
              </span>
            </div>

            {ds.schema_info ? (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left">
                  <thead>
                    <tr className="border-b border-[#2a2d3e] text-[10px] text-[#64748b]">
                      <th className="py-1 font-semibold">Column</th>
                      <th className="py-1 font-semibold">Type</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#2a2d3e] text-xs">
                    {Object.entries(ds.schema_info).map(([colName, colType]) => (
                      <tr key={colName} className="text-[#e2e8f0]">
                        <td className="py-1.5 font-mono text-[11px] truncate max-w-[150px]" title={colName}>
                          {colName}
                        </td>
                        <td className="py-1.5">
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold ${getTypeBadgeColor(colType)}`}>
                            {colType}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-[#64748b]">No schema information detected.</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
