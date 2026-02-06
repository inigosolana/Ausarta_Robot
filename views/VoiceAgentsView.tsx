
import React, { useState } from 'react';
import { Plus, X, ChevronDown, Phone, Play } from 'lucide-react';

interface VoiceAgentsViewProps {
  onStartCall: () => void;
}

const VoiceAgentsView: React.FC<VoiceAgentsViewProps> = ({ onStartCall }) => {
  const [isCreating, setIsCreating] = useState(false);
  
  // Mock data for demo
  const [agents, setAgents] = useState([
    { id: '1', name: 'Real Estate Qualifier', callType: 'Outbound', useCase: 'Lead Gen', description: 'Qualifies leads for real estate investment.' }
  ]);

  if (isCreating) {
    return (
      <div className="space-y-6">
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Create Voice Agent</h1>
            <p className="text-gray-500 text-sm mt-1">Tell us about your use case and we'll create a customized voice agent for you</p>
          </div>
          <button onClick={() => setIsCreating(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400">
            <X size={20} />
          </button>
        </header>

        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 space-y-6">
          <h3 className="text-base font-bold text-gray-900">Agent Details</h3>
          <p className="text-xs text-gray-400 -mt-5">Configure your voice agent settings</p>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Call Type</label>
              <div className="relative">
                <select className="w-full h-10 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer">
                  <option>Inbound (Users call AI)</option>
                  <option>Outbound (AI calls users)</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
              </div>
              <p className="text-[11px] text-gray-400 mt-1">Choose whether users will call your AI or your AI will call users</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Use Case</label>
              <input 
                type="text" 
                placeholder="e.g., Lead Qualification, HR Screening, Customer Support" 
                className="w-full h-10 px-4 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              />
              <p className="text-[11px] text-gray-400 mt-1">Describe the primary purpose of your voice agent</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Activity Description</label>
              <textarea 
                rows={4}
                placeholder="Describe briefly what your voice agent will do (e.g., Qualify leads for real estate, Screen candidates for roles, Handle customer support). This will be a prompt to an LLM."
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all resize-none"
              />
              <p className="text-[11px] text-gray-400 mt-1">This description will be used to generate the AI prompt for your voice agent</p>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button onClick={() => setIsCreating(false)} className="flex-1 py-2.5 bg-gray-400 text-white text-sm font-medium rounded-lg hover:bg-gray-500 transition-colors shadow-sm">
              Create Agent
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
          <h1 className="text-2xl font-bold text-gray-900">Voice Agents</h1>
          <p className="text-gray-500 text-sm mt-1">Design and manage your AI-powered voice representatives</p>
        </div>
        <button 
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#121212] text-white text-sm font-medium rounded-lg hover:bg-black transition-colors shadow-sm"
        >
          <Plus size={18} />
          New Agent
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agents.map((agent) => (
          <div key={agent.id} className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-bold text-gray-900">{agent.name}</h3>
                <span className="text-[10px] uppercase tracking-wider font-bold text-blue-500 bg-blue-50 px-2 py-0.5 rounded-full">{agent.callType}</span>
              </div>
              <button 
                onClick={onStartCall}
                className="p-2 bg-green-500 text-white rounded-full hover:bg-green-600 transition-colors shadow-sm group-hover:scale-110"
              >
                <Phone size={16} fill="white" />
              </button>
            </div>
            <p className="text-sm text-gray-600 line-clamp-2 mb-4">{agent.description}</p>
            <div className="flex items-center gap-4 text-[11px] text-gray-400 font-medium">
              <span>Use Case: {agent.useCase}</span>
              <span>•</span>
              <span>Modified 2h ago</span>
            </div>
          </div>
        ))}
        
        <button 
          onClick={() => setIsCreating(true)}
          className="border-2 border-dashed border-gray-100 rounded-xl p-6 flex flex-col items-center justify-center text-gray-400 hover:border-gray-200 hover:text-gray-500 transition-all min-h-[160px]"
        >
          <Plus size={24} className="mb-2" />
          <span className="text-sm font-medium">Create New Agent</span>
        </button>
      </div>
    </div>
  );
};

export default VoiceAgentsView;
