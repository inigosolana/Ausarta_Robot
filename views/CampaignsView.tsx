
import React, { useState, useEffect } from 'react';
import { Plus, X, Upload, ChevronDown, ChevronRight, Download, FileText, CheckCircle, Clock } from 'lucide-react';

interface Campaign {
  id: number;
  name: string;
  status: string;
  created_at: string;
  agent_id: number;
}

interface Agent {
  id: string;
  name: string;
}

const CampaignsView: React.FC = () => {
  const [isCreating, setIsCreating] = useState(false);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);

  // Form State
  const [name, setName] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('');
  const [dataSource, setDataSource] = useState<'csv' | 'manual' | 'api'>('csv');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [manualNumbers, setManualNumbers] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002';

  useEffect(() => {
    loadCampaigns();
    loadAgents();
  }, []);

  const loadCampaigns = async () => {
    try {
      const res = await fetch(`${API_URL}/api/campaigns`);
      if (res.ok) setCampaigns(await res.json());
    } catch (e) {
      console.error("Error loading campaigns", e);
    }
  };

  const loadAgents = async () => {
    try {
      const res = await fetch(`${API_URL}/api/agents`);
      if (res.ok) {
        const data = await res.json();
        setAgents(data);
        // Auto-select if only one agent exists
        if (data.length > 0) {
          setSelectedAgent(data[0].id.toString());
        }
      }
    } catch (e) { console.error("Error loading agents:", e); }
  };

  const downloadTemplate = () => {
    const csvContent = "phone_number\n+34600112233\n+34611223344";
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "campaign_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleCreate = async () => {
    setLoading(true);
    setError('');

    try {
      let leads: { phone_number: string }[] = [];

      if (dataSource === 'manual') {
        leads = manualNumbers.split('\n')
          .map(n => n.trim())
          .filter(n => n.length > 5)
          .map(n => ({ phone_number: n }));
      } else if (dataSource === 'csv' && csvFile) {
        const text = await csvFile.text();
        const lines = text.split('\n');
        // Simple CSV parser assuming first column or header "phone_number"
        leads = lines
          .filter(line => line.trim() !== '' && !line.includes('phone_number')) // Skip header/empty
          .map(line => {
            const parts = line.split(',');
            return { phone_number: parts[0].trim() };
          })
          .filter(l => l.phone_number.length > 5);
      } else if (dataSource === 'api') {
        // API campaigns start with 0 leads
        leads = [];
      }

      if (dataSource !== 'api' && leads.length === 0) {
        throw new Error("No valid phone numbers found");
      }

      if (!selectedAgent) throw new Error("Please select an agent");

      const res = await fetch(`${API_URL}/api/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaign: {
            name,
            agent_id: parseInt(selectedAgent),
            scheduled_time: scheduledTime || null,
            status: dataSource === 'api' ? 'active' : 'pending'
          },
          leads
        })
      });

      if (!res.ok) throw new Error("Failed to create campaign");

      setIsCreating(false);
      loadCampaigns();
      // Reset form
      setName('');
      setManualNumbers('');
      setCsvFile(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (isCreating) {
    return (
      <div className="space-y-6">
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Create Campaign</h1>
            <p className="text-gray-500 text-sm mt-1">Set up a new campaign to execute calls at scale</p>
          </div>
          <button onClick={() => setIsCreating(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400">
            <X size={20} />
          </button>
        </header>

        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 space-y-6 max-w-2xl mx-auto">
          <h3 className="text-base font-bold text-gray-900">Campaign Details</h3>

          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm border border-red-100">
              {error}
            </div>
          )}

          <div className="space-y-4">
            {/* NAME */}
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Campaign Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Q1 Customer Survey"
                className="w-full h-10 px-4 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              />
            </div>

            {/* AGENT */}
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Agent</label>
              <div className="relative">
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="w-full h-10 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer"
                >
                  <option value="">Select an agent</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
              </div>
            </div>

            {/* DATA SOURCE TYPE */}
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Data Source Type</label>
              <div className="relative">
                <select
                  value={dataSource}
                  onChange={(e) => setDataSource(e.target.value as 'csv' | 'manual' | 'api')}
                  className="w-full h-10 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer"
                >
                  <option value="csv">CSV File</option>
                  <option value="manual">Manual Entry</option>
                  <option value="api">API Webhook</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
              </div>
            </div>

            {/* CSV INPUT */}
            {dataSource === 'csv' && (
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-sm font-semibold text-gray-800">CSV File</label>
                  <button onClick={downloadTemplate} className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                    <Download size={12} /> Download Template
                  </button>
                </div>
                <label className={`flex flex-col items-center justify-center w-full px-4 py-6 border-2 border-dashed rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${csvFile ? 'border-green-300 bg-green-50' : 'border-gray-200'}`}>
                  {csvFile ? (
                    <div className="flex flex-col items-center text-green-700">
                      <CheckCircle size={24} className="mb-2" />
                      <span className="text-sm font-medium">{csvFile.name}</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center text-gray-500">
                      <Upload size={24} className="mb-2" />
                      <span className="text-sm">Click to upload or drag and drop</span>
                      <span className="text-xs text-gray-400 mt-1">.csv files only</span>
                    </div>
                  )}
                  <input type="file" className="hidden" accept=".csv" onChange={(e) => setCsvFile(e.target.files?.[0] || null)} />
                </label>
              </div>
            )}

            {/* MANUAL INPUT */}
            {dataSource === 'manual' && (
              <div>
                <label className="block text-sm font-semibold text-gray-800 mb-1">Phone Numbers</label>
                <textarea
                  value={manualNumbers}
                  onChange={(e) => setManualNumbers(e.target.value)}
                  placeholder="+34600123456&#10;+34600999888"
                  className="w-full h-32 px-4 py-3 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all font-mono"
                />
                <p className="text-[11px] text-gray-400 mt-1">Enter one phone number per line.</p>
              </div>
            )}

            {/* API INFO */}
            {dataSource === 'api' && (
              <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-blue-800 font-semibold text-sm">
                  <CheckCircle size={16} />
                  <span>API Trigger Configured</span>
                </div>
                <p className="text-xs text-blue-600 leading-relaxed">
                  Upon creation, you will receive a unique Webhook URL. You can send <code>POST</code> requests to this endpoint with a <code>phone_number</code> to instantly trigger calls for this campaign.
                </p>
                <div className="mt-2 bg-white p-2 rounded border border-blue-100 font-mono text-xs text-gray-600">
                  POST {API_URL}/api/campaigns/{'{id}'}/trigger
                </div>
              </div>
            )}

            {/* ADVANCED */}
            <button
              onClick={() => setAdvancedOpen(!advancedOpen)}
              className="flex items-center justify-between w-full p-4 border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors"
            >
              <span className="text-sm font-bold text-gray-800">Advanced Settings / Scheduling</span>
              <ChevronRight size={18} className={`text-gray-400 transition-transform ${advancedOpen ? 'rotate-90' : ''}`} />
            </button>

            {advancedOpen && (
              <div className="p-4 bg-gray-50 rounded-xl space-y-3">
                <label className="block text-sm font-medium text-gray-700">Schedule Start Time</label>
                <input
                  type="datetime-local"
                  value={scheduledTime}
                  onChange={(e) => setScheduledTime(e.target.value)}
                  className="w-full h-10 px-3 bg-white border border-gray-200 rounded-lg text-sm"
                />
                <p className="text-xs text-gray-400">Leave blank to start immediately after creation (requires backend worker).</p>
              </div>
            )}
          </div>

          <div className="flex gap-3 pt-4 border-t border-gray-50">
            <button
              onClick={handleCreate}
              disabled={loading}
              className="flex-1 py-2.5 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors shadow-sm disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Launch Campaign'}
            </button>
            <button onClick={() => setIsCreating(false)} className="px-6 py-2.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
          <p className="text-gray-500 text-sm mt-1">Manage your bulk outbound call campaigns</p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#121212] text-white text-sm font-medium rounded-lg hover:bg-black transition-colors shadow-sm"
        >
          <Plus size={18} />
          Create Campaign
        </button>
      </header>

      {/* List */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        {campaigns.length === 0 ? (
          <div className="p-12 flex flex-col items-center justify-center text-center">
            <FileText size={48} className="text-gray-200 mb-4" />
            <h3 className="text-gray-900 font-medium mb-1">No campaigns yet</h3>
            <p className="text-gray-400 text-sm mb-6">Create your first campaign to start calling leads.</p>
            <button
              onClick={() => setIsCreating(true)}
              className="px-4 py-2 bg-gray-50 text-gray-700 rounded-lg text-sm hover:bg-gray-100 font-medium transition-colors"
            >
              Create Campaign
            </button>
          </div>
        ) : (
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 text-gray-500 font-medium border-b border-gray-100">
              <tr>
                <th className="px-6 py-3">Campaign Name</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Scheduled</th>
                <th className="px-6 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {campaigns.map(c => (
                <tr key={c.id} className="hover:bg-gray-50/50">
                  <td className="px-6 py-4 font-medium text-gray-900">{c.name}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize 
                        ${c.status === 'completed' ? 'bg-green-100 text-green-800' :
                        c.status === 'running' || c.status === 'active' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {c.scheduled_time ? new Date(c.scheduled_time).toLocaleString() : '-'}
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default CampaignsView;
