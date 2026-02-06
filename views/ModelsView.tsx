
import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

const ModelsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'LLM' | 'Voice' | 'Transcriber' | 'Embedding'>('LLM');

  const tabs = ['LLM', 'Voice', 'Transcriber', 'Embedding'];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">AI Models Configuration</h1>
        <p className="text-gray-500 text-sm mt-1">Configure your AI model, voice, and transcription services.</p>
      </header>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="flex bg-gray-50/30 p-1 m-4 rounded-lg border border-gray-100">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`
                flex-1 py-1.5 text-xs font-medium rounded-md transition-all
                ${activeTab === tab 
                  ? 'bg-white text-gray-900 shadow-sm border border-gray-100' 
                  : 'text-gray-500 hover:text-gray-700'
                }
              `}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="px-8 pb-8 pt-4 space-y-6 min-h-[200px]">
          <div>
            <label className="block text-sm font-semibold text-gray-800 mb-2">Provider</label>
            <div className="relative">
              <select className="w-full h-10 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer">
                <option value="">Select provider</option>
                <option>OpenAI</option>
                <option>Anthropic</option>
                <option>Google Gemini</option>
                <option>Groq</option>
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col items-stretch">
        <button className="py-2.5 bg-[#121212] text-white text-sm font-medium rounded-lg hover:bg-black transition-colors shadow-sm">
          Save Configuration
        </button>
      </div>
    </div>
  );
};

export default ModelsView;
