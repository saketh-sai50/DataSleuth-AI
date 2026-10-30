import React, { useState, useRef } from 'react';
import { Investigation, Dataset } from '../types';

interface MissingDataPanelProps {
  investigation: Investigation | null;
  onUploadMissingFile: (file: File) => Promise<Dataset>;
  onContinueInvestigation: (newDatasetIds: number[]) => void;
  isContinuing: boolean;
}

export const MissingDataPanel: React.FC<MissingDataPanelProps> = ({
  investigation,
  onUploadMissingFile,
  onContinueInvestigation,
  isContinuing,
}) => {
  const [uploadingName, setUploadingName] = useState<string | null>(null);
  const [uploadedNewDatasets, setUploadedNewDatasets] = useState<Dataset[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const activeDatasetNameRef = useRef<string>('');

  if (!investigation || investigation.missing_datasets.length === 0) {
    return null;
  }

  const handleUploadClick = (missingDatasetName: string) => {
    activeDatasetNameRef.current = missingDatasetName;
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      const targetName = activeDatasetNameRef.current;
      
      setUploadingName(targetName);
      setError(null);

      try {
        const dataset = await onUploadMissingFile(file);
        setUploadedNewDatasets((prev) => [...prev, dataset]);
      } catch (err: any) {
        setError(`Failed to upload ${targetName}: ${err.message || 'Error occurred.'}`);
      } finally {
        setUploadingName(null);
      }
    }
  };

  const handleContinue = () => {
    if (uploadedNewDatasets.length === 0) return;
    const ids = uploadedNewDatasets.map((d) => d.id);
    onContinueInvestigation(ids);
    setUploadedNewDatasets([]);
  };

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 space-y-4">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".csv, .xlsx"
        className="hidden"
      />

      <div>
        <h2 className="text-sm font-semibold text-[#f59e0b] flex items-center space-x-2">
          <svg className="h-4.5 w-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span>Missing Information Detected</span>
        </h2>
        <p className="text-[10px] text-[#94a3b8] mt-0.5">
          The agent needs supplementary evidence to validate hypotheses
        </p>
      </div>

      {error && <p className="text-xs text-red-500 font-medium">{error}</p>}

      {/* Follow-up Questions and Upload Actions */}
      <div className="space-y-3.5">
        {investigation.missing_datasets.map((missingName, idx) => {
          const isUploaded = uploadedNewDatasets.some(
            (d) => d.filename.toLowerCase() === missingName.toLowerCase()
          );
          const isUploading = uploadingName === missingName;
          const question = investigation.follow_up_questions[idx] || 
            `Do you have the dataset '${missingName}' available to upload?`;

          return (
            <div key={missingName} className="bg-[#141620] border border-[#2a2d3e] rounded-lg p-3 space-y-2">
              <div className="flex items-start space-x-2">
                <div className="bg-[#f59e0b]/10 text-[#f59e0b] p-1 rounded mt-0.5">
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2.5}
                      d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-xs text-[#e2e8f0] font-medium leading-relaxed">
                    {question}
                  </p>
                  <p className="text-[10px] text-[#64748b] mt-0.5">
                    Required source: <span className="font-mono text-white">{missingName}</span>
                  </p>
                </div>
              </div>

              <div className="flex justify-end pt-1">
                {isUploaded ? (
                  <span className="text-[10px] text-[#10b981] font-semibold flex items-center space-x-1">
                    <svg className="h-4.5 w-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                    </svg>
                    <span>Uploaded & Ready</span>
                  </span>
                ) : (
                  <button
                    onClick={() => handleUploadClick(missingName)}
                    disabled={isUploading || isContinuing}
                    className="bg-[#2a2d3e] hover:bg-[#6366f1] disabled:opacity-50 text-white text-[10px] font-semibold px-3 py-1 rounded transition-colors flex items-center space-x-1"
                  >
                    {isUploading ? (
                      <span className="animate-pulse">Uploading...</span>
                    ) : (
                      <>
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                        </svg>
                        <span>Upload Dataset</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Resume Investigation Action */}
      {uploadedNewDatasets.length > 0 && (
        <button
          onClick={handleContinue}
          disabled={isContinuing}
          className="w-full bg-[#10b981] hover:bg-[#059669] disabled:opacity-50 text-white text-xs font-semibold py-2 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2"
        >
          {isContinuing ? (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span>Resume Investigation</span>
            </>
          )}
        </button>
      )}
    </div>
  );
};
