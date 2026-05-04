import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, FileText, Loader2, CheckCircle, Download, BookOpen, Upload, FileUp, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface JobStatus {
  status: 'processing' | 'completed' | 'failed' | 'not_found';
  data?: {
    output: string;
    sources: string[];
    project_dir: string;
  };
  error?: string;
}

// Live Deployment Config
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://academicwritermvp.onrender.com';

function App() {
  const [topic, setTopic] = useState('');
  const [wordCount, setWordCount] = useState(1000);
  const [citationStyle, setCitationStyle] = useState('APA 7');
  const [discipline, setDiscipline] = useState('Computer Science');
  const [optimizationPrompt, setOptimizationPrompt] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files));
    }
  };

  const addFiles = (newFiles: File[]) => {
    setFiles(prev => {
      const combined = [...prev, ...newFiles];
      return combined.slice(0, 20); // Maintain 20 file limit
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const startResearch = async () => {
    try {
      const formData = new FormData();
      formData.append('topic', topic);
      formData.append('word_count', wordCount.toString());
      formData.append('citation_style', citationStyle);
      formData.append('discipline', discipline);
      formData.append('optimization_prompt', optimizationPrompt);
      
      files.forEach((file) => {
        formData.append('files', file);
      });

      const response = await axios.post(`${API_BASE_URL}/research`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setJobId(response.data.job_id);
      setJobStatus({ status: 'processing' });
    } catch (error) {
      console.error('Error starting research:', error);
      alert('Failed to start research job');
    }
  };

  useEffect(() => {
    let interval: number;
    if (jobId && jobStatus?.status === 'processing') {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/research/${jobId}`);
          setJobStatus(response.data);
          if (response.data.status !== 'processing') {
            clearInterval(interval);
          }
        } catch (error) {
          console.error('Error polling job status:', error);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [jobId, jobStatus?.status]);

  return (
    <div className="min-h-screen w-full flex flex-col items-center p-8 bg-gray-50">
      <header className="mb-12 text-center">
        <h1 className="text-4xl font-bold text-gray-900 flex items-center justify-center gap-3">
          <BookOpen className="text-blue-600 w-10 h-10" />
          Academic Writer MVP
        </h1>
        <p className="text-gray-600 mt-2 text-lg">Autonomous research and writing pipeline</p>
      </header>

      <main className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Configuration Section */}
        <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col gap-4">
          <h2 className="text-xl font-semibold flex items-center gap-2 mb-2">
            <Search className="w-5 h-5 text-blue-500" />
            Project Settings
          </h2>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Research Topic</label>
            <textarea 
              className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
              rows={3}
              placeholder="e.g., The impact of Large Language Models on software engineering productivity"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Evidence Files (Max 20)</label>
            <div className="flex flex-col gap-2">
              <label 
                className={`flex items-center justify-center gap-2 p-4 border-2 border-dashed rounded-lg cursor-pointer transition-all ${
                  isDragging ? 'bg-blue-100 border-blue-500 scale-[1.02]' : 'hover:bg-blue-50 border-gray-300 hover:border-blue-400 text-gray-500'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <Upload className={`w-5 h-5 ${isDragging ? 'text-blue-600 animate-bounce' : ''}`} />
                <span>{isDragging ? 'Drop files here' : 'Upload or Drag & Drop PDFs, DOCX, Images, or CSV/Excel'}</span>
                <input 
                  type="file" 
                  multiple 
                  className="hidden" 
                  accept=".pdf,.docx,.doc,.png,.jpg,.jpeg,.txt,.csv,.xlsx,.xls"
                  onChange={handleFileChange}
                />
              </label>
              
              {files.length > 0 && (
                <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto p-1 mt-1">
                  {files.map((file, i) => (
                    <div key={i} className="flex items-center gap-1 bg-white px-2 py-1 rounded text-xs border border-gray-200 shadow-sm text-gray-600 group">
                      <FileUp className={`w-3 h-3 ${file.name.match(/\.(csv|xlsx|xls)$/i) ? 'text-green-500' : 'text-blue-500'}`} />
                      <span className="truncate max-w-[120px]">{file.name}</span>
                      <button 
                        onClick={() => removeFile(i)} 
                        className="text-gray-400 hover:text-red-500 transition-colors ml-1 p-0.5 rounded-full hover:bg-red-50"
                        title="Remove file"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1 text-blue-600 flex items-center gap-1">
              Optimization Prompt (Optional)
            </label>
            <textarea 
              className="w-full p-3 border border-blue-100 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none bg-blue-50/30 text-sm"
              rows={2}
              placeholder="e.g., Use the methodology from the lab results DOCX. Focus on empirical evidence."
              value={optimizationPrompt}
              onChange={(e) => setOptimizationPrompt(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Word Count</label>
              <input 
                type="number" 
                className="w-full p-2 border rounded-lg"
                value={wordCount}
                onChange={(e) => setWordCount(parseInt(e.target.value))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Citation Style</label>
              <select 
                className="w-full p-2 border rounded-lg"
                value={citationStyle}
                onChange={(e) => setCitationStyle(e.target.value)}
              >
                <option>APA 7</option>
                <option>MLA 9</option>
                <option>IEEE</option>
                <option>Chicago</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Discipline</label>
            <input 
              className="w-full p-2 border rounded-lg"
              value={discipline}
              onChange={(e) => setDiscipline(e.target.value)}
            />
          </div>

          <button 
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 mt-4 disabled:opacity-50"
            onClick={startResearch}
            disabled={!topic || jobStatus?.status === 'processing'}
          >
            {jobStatus?.status === 'processing' ? (
              <>
                <Loader2 className="animate-spin w-5 h-5" />
                Processing...
              </>
            ) : (
              'Start Autonomous Research'
            )}
          </button>
        </section>

        {/* Status & Results Section */}
        <section className="md:col-span-2 bg-white p-6 rounded-xl shadow-sm border border-gray-100 min-h-[500px]">
          {!jobStatus ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-400">
              <FileText className="w-16 h-16 mb-4 opacity-20" />
              <p>Start a job to see results</p>
            </div>
          ) : jobStatus.status === 'processing' ? (
            <div className="h-full flex flex-col items-center justify-center">
              <div className="relative">
                <div className="absolute inset-0 animate-ping rounded-full bg-blue-100 scale-150 opacity-75"></div>
                <Loader2 className="w-12 h-12 text-blue-600 animate-spin relative" />
              </div>
              <h3 className="mt-8 text-xl font-medium">Conducting Research Pipeline</h3>
              <ul className="mt-6 space-y-3 text-sm text-gray-600 w-full max-w-xs">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-500" /> Generating Boolean Queries
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div> 
                  Iterating Searches & Downloads
                </li>
                <li className="flex items-center gap-2 opacity-40">
                  <div className="w-4 h-4 rounded-full border-2 border-gray-300"></div> 
                  Parsing PDFs & Synthesizing Evidence
                </li>
                <li className="flex items-center gap-2 opacity-40">
                  <div className="w-4 h-4 rounded-full border-2 border-gray-300"></div> 
                  Drafting Academic Paper
                </li>
              </ul>
            </div>
          ) : jobStatus.status === 'completed' && jobStatus.data ? (
            <div className="h-full flex flex-col">
              <div className="flex justify-between items-center mb-6 pb-4 border-b">
                <h2 className="text-2xl font-bold">Generated Academic Paper</h2>
                <div className="flex gap-2">
                  <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> Fully Cited
                  </span>
                  <button className="text-blue-600 hover:text-blue-800 p-1">
                    <Download className="w-5 h-5" />
                  </button>
                </div>
              </div>
              
              <div className="prose prose-sm max-w-none overflow-y-auto max-h-[600px] text-gray-800">
                <ReactMarkdown>{jobStatus.data.output}</ReactMarkdown>
              </div>

              <div className="mt-8 pt-6 border-t">
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-blue-500" />
                  Source Evidence Matrix
                </h3>
                <div className="flex flex-wrap gap-2">
                  {jobStatus.data.sources.map((source, i) => (
                    <div key={i} className="bg-gray-100 px-3 py-2 rounded-lg text-xs font-medium text-gray-600 border flex items-center gap-2">
                      <FileText className="w-3 h-3" />
                      {source.split('\\').pop()?.split('/').pop() || `Source ${i+1}`}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-red-500">
              <p>Job failed: {jobStatus.error || 'Unknown error'}</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
