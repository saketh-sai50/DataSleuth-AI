import React, { useState, useRef } from 'react';
import { Dataset } from '../types';
import { datasetsApi } from '../api/client';


interface UploadPanelProps {
  datasets: Dataset[];
  selectedDatasetIds: number[];
  onSelectDataset: (id: number) => void;
  onUploadSuccess: (dataset: Dataset) => void;
  onDeleteDataset: (id: number) => void;
}

export const UploadPanel: React.FC<UploadPanelProps> = ({
  datasets,
  selectedDatasetIds,
  onSelectDataset,
  onUploadSuccess,
  onDeleteDataset,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const processFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'csv' && ext !== 'xlsx') {
      setError('Only CSV (.csv) and Excel (.xlsx) files are supported.');
      return;
    }

    setError(null);
    setIsUploading(true);

    try {
      const dataset = await datasetsApi.upload(file);
      onUploadSuccess(dataset);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload dataset.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const formatSize = (bytes: number | null): string => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3e] rounded-xl p-5 flex flex-col h-full space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-white">Datasets</h2>
        <p className="text-xs text-[#94a3b8]">Upload and manage data sources</p>
      </div>

      {/* Drag & Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={triggerFileInput}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center space-y-2 ${
          isDragging
            ? 'border-[#6366f1] bg-[#6366f1]/5'
            : 'border-[#2a2d3e] hover:border-[#6366f1]/50 hover:bg-[#1f2230]'
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".csv, .xlsx"
          className="hidden"
        />

        {isUploading ? (
          <div className="flex flex-col items-center space-y-2">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#6366f1]"></div>
            <p className="text-sm text-[#94a3b8]">Analyzing dataset...</p>
          </div>
        ) : (
          <>
            <svg
              className="h-8 w-8 text-[#64748b]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-sm font-medium text-[#e2e8f0]">
              Drag & drop CSV or Excel
            </p>
            <p className="text-xs text-[#64748b]">or click to browse files</p>
          </>
        )}
      </div>

      {error && <p className="text-xs text-red-500 font-medium">{error}</p>}

      {/* Datasets List */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 max-h-[350px]">
        {datasets.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-xs text-[#64748b]">No datasets uploaded yet.</p>
          </div>
        ) : (
          datasets.map((ds) => {
            const isSelected = selectedDatasetIds.includes(ds.id);
            return (
              <div
                key={ds.id}
                className={`border rounded-lg p-3 transition-all duration-200 flex items-start space-x-3 ${
                  isSelected
                    ? 'border-[#6366f1]/50 bg-[#6366f1]/5'
                    : 'border-[#2a2d3e] bg-[#141620]'
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onSelectDataset(ds.id)}
                  className="mt-1 h-4.5 w-4.5 rounded border-[#2a2d3e] text-[#6366f1] focus:ring-[#6366f1]"
                />

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate" title={ds.filename}>
                    {ds.filename}
                  </p>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-[10px] bg-[#2a2d3e] px-1.5 py-0.5 rounded text-[#94a3b8] uppercase font-semibold">
                      {ds.file_type}
                    </span>
                    <span className="text-[10px] text-[#64748b]">
                      {ds.row_count ? `${ds.row_count} rows` : '0 rows'}
                    </span>
                    <span className="text-[10px] text-[#64748b]">
                      {formatSize(ds.file_size_bytes)}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => onDeleteDataset(ds.id)}
                  className="text-[#64748b] hover:text-red-500 transition-colors p-1"
                  title="Delete dataset"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
