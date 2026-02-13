import React, { useState, useEffect } from 'react';
import { ChevronDown, Save, Loader2, CheckCircle, AlertCircle } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || window.location.origin + '/api' || 'http://localhost:8002/api';

const ModelsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState('LLM');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const [settings, setSettings] = useState({
    llm_provider: 'groq',
    llm_model: 'llama-3.3-70b-versatile'
  });

  const tabs = ['LLM', 'Voice', 'Transcriber'];

  // Load settings on mount
  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/settings`);
      if (res.ok) {
        const data = await res.json();
        setSettings(prev => ({ ...prev, ...data }));
      }
    } catch (e) {
      console.error("Error fetching settings", e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });

      if (res.ok) {
        setMessage({ type: 'success', text: 'Configuration saved successfully!' });
        // Recargar para confirmar (o no hace falta)
      } else {
        setMessage({ type: 'error', text: 'Failed to save configuration.' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Network error saving configuration.' });
    } finally {
      setSaving(false);
    }
  };

  const getModelOptions = () => {
    if (settings.llm_provider === 'groq') {
      return [
        'llama-3.3-70b-versatile',
        'mixtral-8x7b-32768'
      ];
    } else if (settings.llm_provider === 'google') {
      return [
        'models/gemini-2.0-flash',
        'models/gemini-2.0-flash-lite',
        'models/gemini-1.5-flash'
      ];
    } else if (settings.llm_provider === 'deepseek') {
      return [
        'deepseek-chat',
        'deepseek-reasoner'
      ];
    } else if (settings.llm_provider === 'openai') {
      return [
        'gpt-4o',
        'gpt-4o-mini',
        'gpt-4-turbo'
      ];
    }
    return [];
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">AI Models Configuration</h1>
        <p className="text-gray-500 text-sm mt-1">Configure your AI model, voice, and transcription services.</p>
      </header>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="border-b border-gray-100 bg-gray-50/50 px-6 pt-4">
          <div className="flex gap-6">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`
                  pb-3 text-sm font-medium border-b-2 transition-all px-1
                  ${activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-8 min-h-[300px]">
          {loading ? (
            <div className="flex justify-center items-center h-40 text-gray-400">
              <Loader2 className="animate-spin w-8 h-8" />
            </div>
          ) : activeTab === 'LLM' ? (
            <div className="space-y-6 max-w-lg">
              <div>
                <label className="block text-sm font-bold text-gray-700 mb-2">LLM Provider</label>
                <div className="relative">
                  <select
                    value={settings.llm_provider}
                    onChange={(e) => setSettings({ ...settings, llm_provider: e.target.value })}
                    className="w-full h-11 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer"
                  >
                    <option value="openai">OpenAI (GPT-4o, mini)</option>
                    <option value="groq">Groq (Llama 3, Mixtral)</option>
                    <option value="google">Google Gemini</option>
                    <option value="deepseek">DeepSeek (V3, R1)</option>
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  {settings.llm_provider === 'openai'
                    ? 'Requires OPENAI_API_KEY in environment variables.'
                    : settings.llm_provider === 'google'
                      ? 'Requires GOOGLE_API_KEY in environment variables.'
                      : settings.llm_provider === 'deepseek'
                        ? 'Requires DEEPSEEK_API_KEY in environment variables.'
                        : 'Requires GROQ_API_KEY in environment variables.'}
                </p>
              </div>

              <label className="block text-sm font-bold text-gray-700 mb-2">Model Name</label>
              <div className="relative">
                <select
                  value={settings.llm_model}
                  onChange={(e) => setSettings({ ...settings, llm_model: e.target.value })}
                  className="w-full h-11 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer"
                >
                  {getModelOptions().map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
              </div>

              {/* Custom Model Input (Optional) - Could be implemented if users really need it, but dropdown is safer */}
              {/* For now, if they want custom they can stick to the list or I'll add a conditional input later if requested. 
                    Actually, let's keep it simple as requested: "QUE NO TENGAS QUE ESCRIBIRLO" */}

              <p className="text-xs text-gray-400 mt-2">
                Select the AI model you want to use for the conversation.
              </p>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-400">
              <p>Configuration for <strong>{activeTab}</strong> coming soon.</p>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-8 py-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
          <div>
            {message && (
              <div className={`flex items-center gap-2 text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                {message.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
                {message.text}
              </div>
            )}
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-black transition-colors shadow-sm disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {saving ? <Loader2 className="animate-spin w-4 h-4" /> : <Save className="w-4 h-4" />}
            Save Changes
          </button>
        </div>
      </div>
    </div >
  );
};

export default ModelsView;
