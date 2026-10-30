import React, { useState, useEffect } from 'react';
import { UploadPanel } from '../components/UploadPanel';
import { ChatPanel, ChatMessage } from '../components/ChatPanel';
import { DatasetSummary } from '../components/DatasetSummary';
import { InvestigationTimeline } from '../components/InvestigationTimeline';
import { MissingDataPanel } from '../components/MissingDataPanel';
import { HypothesisList } from '../components/HypothesisList';
import { ReportViewer } from '../components/ReportViewer';
import {
  Dataset,
  Investigation,
  Report,
} from '../types';
import {
  datasetsApi,
  investigationsApi,
  reportsApi,
} from '../api/client';
export const Dashboard: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetIds, setSelectedDatasetIds] = useState<number[]>([]);
  
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [currentInvestigation, setCurrentInvestigation] = useState<Investigation | null>(null);
  const [currentReport, setCurrentReport] = useState<Report | null>(null);
  
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isContinuing, setIsContinuing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load datasets and investigations on mount
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const dsRes = await datasetsApi.list();
      setDatasets(dsRes.datasets);

      const invs = await investigationsApi.list();
      setInvestigations(invs);
    } catch (err) {
      console.error('Failed to load initial datasets/investigations', err);
    }
  };

  const handleSelectDataset = (id: number) => {
    setSelectedDatasetIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const handleUploadSuccess = (dataset: Dataset) => {
    setDatasets((prev) => [dataset, ...prev]);
  };

  const handleDeleteDataset = async (id: number) => {
    try {
      await datasetsApi.delete(id);
      setDatasets((prev) => prev.filter((d) => d.id !== id));
      setSelectedDatasetIds((prev) => prev.filter((d) => d !== id));
    } catch (err) {
      setError('Failed to delete dataset.');
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;

    setError(null);
    const userMsg: ChatMessage = { role: 'user', content };
    setChatMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      if (!currentInvestigation) {
        // No active session: Start a new investigation!
        if (selectedDatasetIds.length === 0) {
          setChatMessages((prev) => [
            ...prev,
            {
              role: 'ai',
              content: 'Please select one or more datasets from the left panel before starting an investigation.',
            },
          ]);
          setIsLoading(false);
          return;
        }

        const data = await investigationsApi.analyze(content, selectedDatasetIds);
        
        // Retrieve newly created investigation
        const invs = await investigationsApi.list();
        setInvestigations(invs);
        
        if (invs.length > 0) {
          const newInv = invs[0]; // latest
          setCurrentInvestigation(newInv);
          
          const stepsSummary = data.plan.plan_steps
            .map((s: any) => `Step ${s.step}: ${s.action}`)
            .join('\n');

          const aiResponse: ChatMessage = {
            role: 'ai',
            content: `I have started the investigation!\n\n**Execution Plan:**\n${stepsSummary}\n\nI have generated ${newInv.hypotheses.length} root cause hypotheses. Let me know if you would like me to compile the business report.`,
            actions: ['Generate Report', ...newInv.follow_up_questions.slice(0, 2)],
          };
          setChatMessages((prev) => [...prev, aiResponse]);
        }
      } else {
        // Conversational chat on existing investigation context
        // Detect "generate/create/build/make/compile report" in any case
        const reportTrigger = /\b(generate|create|build|make|compile|show|produce)\s+(a\s+)?(business\s+)?report\b/i;
        if (reportTrigger.test(content.trim())) {
          setChatMessages((prev) => [
            ...prev,
            { role: 'ai', content: '📊 Compiling your PowerBI-style business report with charts and visualizations...' },
          ]);
          await handleGenerateReport(currentInvestigation.id);
          setIsLoading(false);
          return;
        }

        const res = await reportsApi.chat(content, currentInvestigation.id);
        const aiResponse: ChatMessage = {
          role: 'ai',
          content: res.response,
          actions: res.suggested_actions,
        };
        setChatMessages((prev) => [...prev, aiResponse]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to process message.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadMissingFile = async (file: File): Promise<Dataset> => {
    const ds = await datasetsApi.upload(file);
    setDatasets((prev) => [ds, ...prev]);
    return ds;
  };

  const handleContinueInvestigation = async (newDatasetIds: number[]) => {
    if (!currentInvestigation) return;
    setIsContinuing(true);
    setError(null);

    try {
      const res = await investigationsApi.continue(currentInvestigation.id, newDatasetIds);
      setCurrentInvestigation(res.investigation);
      
      const newValidations = res.new_validations;
      
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'ai',
          content: `I have resumed the investigation with the new dataset(s)!\n\n**Status:** ${newValidations.summary}\n\nI have evaluated the hypotheses. Would you like me to compile the updated report?`,
          actions: ['Generate Report'],
        },
      ]);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resume investigation.');
    } finally {
      setIsContinuing(false);
    }
  };

  const handleGenerateReport = async (invId: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const report = await reportsApi.generate(invId);
      setCurrentReport(report);

      // Refresh investigation to show completed status
      const updatedInv = await investigationsApi.get(invId);
      setCurrentInvestigation(updatedInv);

      setChatMessages((prev) => [
        ...prev,
        {
          role: 'ai',
          content: `The business report has been compiled successfully! You can view it below. Confidence: ${(report.overall_confidence * 100).toFixed(0)}%.`,
        },
      ]);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate report.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectInvestigation = async (id: number) => {
    setError(null);
    setIsLoading(true);
    try {
      const inv = await investigationsApi.get(id);
      setCurrentInvestigation(inv);
      
      // Attempt to load associated report
      try {
        const reports = await reportsApi.list();
        const linkedReport = reports.find((r) => r.investigation_id === id);
        setCurrentReport(linkedReport || null);
      } catch (e) {
        setCurrentReport(null);
      }

      setChatMessages([
        {
          role: 'ai',
          content: `Loaded investigation session #${id}: "${inv.question}"\nStatus: ${inv.status.toUpperCase()}`,
          actions: inv.status === 'completed' ? [] : ['Generate Report'],
        },
      ]);
    } catch (err) {
      setError('Failed to load investigation details.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewSession = () => {
    setCurrentInvestigation(null);
    setCurrentReport(null);
    setChatMessages([]);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#0f1117] flex flex-col">
      {/* Top Navigation */}
      <header className="bg-[#1a1d27] border-b border-[#2a2d3e] px-6 py-4 flex justify-between items-center z-10">
        <div className="flex items-center space-x-3">
          <div className="bg-[#6366f1] p-2 rounded-lg text-white">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div>
            <h1 className="text-md font-bold text-white tracking-wide">IDAA</h1>
            <p className="text-[10px] text-[#64748b] font-medium uppercase">Investigative AI Data Analyst</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {currentInvestigation && (
            <button
              onClick={handleNewSession}
              className="bg-[#6366f1]/10 hover:bg-[#6366f1]/20 border border-[#6366f1]/30 text-[#6366f1] px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors"
            >
              Start New Investigation
            </button>
          )}

          {investigations.length > 0 && (
            <select
              onChange={(e) => handleSelectInvestigation(Number(e.target.value))}
              value={currentInvestigation?.id || ''}
              className="bg-[#141620] border border-[#2a2d3e] text-xs text-[#e2e8f0] px-3 py-1.5 rounded-lg focus:outline-none focus:border-[#6366f1]"
            >
              <option value="" disabled>Load Session...</option>
              {investigations.map((inv) => (
                <option key={inv.id} value={inv.id}>
                  Session #{inv.id}: {inv.question.substring(0, 25)}...
                </option>
              ))}
            </select>
          )}
        </div>
      </header>

      {/* Main Grid */}
      <main className="flex-1 p-6 grid grid-cols-1 xl:grid-cols-4 gap-6 overflow-hidden">
        {/* Sidebar panels */}
        <div className="xl:col-span-1 flex flex-col space-y-6">
          <UploadPanel
            datasets={datasets}
            selectedDatasetIds={selectedDatasetIds}
            onSelectDataset={handleSelectDataset}
            onUploadSuccess={handleUploadSuccess}
            onDeleteDataset={handleDeleteDataset}
          />
          <DatasetSummary datasets={datasets} selectedDatasetIds={selectedDatasetIds} />
        </div>

        {/* Center Main panel */}
        <div className="xl:col-span-3 flex flex-col space-y-6">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-xs font-semibold">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Timeline & Chat column */}
            <div className="lg:col-span-2 flex flex-col space-y-6">
              <InvestigationTimeline investigation={currentInvestigation} />
              <ChatPanel
                messages={chatMessages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                onActionClick={(action) => handleSendMessage(action)}
              />

              {/* ── Generate Report Banner ── */}
              {currentInvestigation && (
                <div className={`rounded-xl border p-5 flex items-center justify-between gap-4 transition-all ${
                  currentReport
                    ? 'bg-[#10b981]/5 border-[#10b981]/20'
                    : 'bg-gradient-to-r from-[#10b981]/10 to-[#059669]/5 border-[#10b981]/30 shadow-lg shadow-[#10b981]/5'
                }`}>
                  <div className="flex items-center space-x-3">
                    <div className={`p-2.5 rounded-lg ${ currentReport ? 'bg-[#10b981]/10' : 'bg-[#10b981]/20'}`}>
                      <svg className="h-5 w-5 text-[#10b981]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {currentReport ? '✅ Report Generated' : 'PowerBI-Style Report'}
                      </p>
                      <p className="text-[11px] text-[#64748b]">
                        {currentReport
                          ? `Confidence: ${(currentReport.overall_confidence * 100).toFixed(0)}% · Charts · KPIs · Recommendations`
                          : 'Compile charts, KPIs, root causes & recommendations into a full business report'}
                      </p>
                    </div>
                  </div>
                  {!currentReport && (
                    <button
                      id="generate-report-btn"
                      onClick={() => handleGenerateReport(currentInvestigation.id)}
                      disabled={isLoading}
                      className="flex-shrink-0 bg-[#10b981] hover:bg-[#059669] disabled:opacity-50 text-white px-5 py-2.5 rounded-lg text-sm font-bold transition-all flex items-center space-x-2 shadow-lg shadow-[#10b981]/20 hover:shadow-[#10b981]/40 hover:scale-105 active:scale-95"
                    >
                      {isLoading ? (
                        <>
                          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                          </svg>
                          <span>Compiling...</span>
                        </>
                      ) : (
                        <>
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <span>Generate Report</span>
                        </>
                      )}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Hypotheses & Missing Data column */}
            <div className="lg:col-span-1 flex flex-col space-y-6">
              {currentInvestigation && (
                <>
                  <MissingDataPanel
                    investigation={currentInvestigation}
                    onUploadMissingFile={handleUploadMissingFile}
                    onContinueInvestigation={handleContinueInvestigation}
                    isContinuing={isContinuing}
                  />
                  <HypothesisList hypotheses={currentInvestigation.hypotheses} />
                </>
              )}
            </div>
          </div>

          {/* Full-width Report Viewer */}
          {currentReport && (
            <div className="pt-2 animate-fadeIn">
              <ReportViewer report={currentReport} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
};
export default Dashboard;
