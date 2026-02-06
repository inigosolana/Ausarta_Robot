
import React from 'react';
import { ChevronDown } from 'lucide-react';

const TelephonyView: React.FC = () => {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Telephony Configuration</h1>
        <p className="text-gray-500 text-sm mt-1">Configure your telephony provider for outbound calls.</p>
      </header>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 space-y-6">
        <div>
          <label className="block text-sm font-semibold text-gray-800 mb-2">Telephony Provider</label>
          <div className="relative">
            <select className="w-full h-10 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer">
              <option>LCR (Generic SIP / Asterisk)</option>
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
          </div>
        </div>

        <div className="bg-gray-50/50 rounded-lg p-4 border border-gray-100">
          <h3 className="text-sm font-semibold text-gray-800 mb-1">LCR Configuration</h3>
          <p className="text-xs text-gray-500 leading-relaxed">
            Using local Asterisk/LCR trunk. No additional credentials required here. Ensure your docker-compose is configured with proper Asterisk/ARI environment variables.
          </p>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-800 mb-2">From Numbers (Comma separated)</label>
          <input 
            type="text" 
            placeholder="e.g. +34944771453, +34988..." 
            className="w-full h-10 px-4 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
          />
          <p className="text-[11px] text-gray-400 mt-2">Numbers that will appear as Caller ID.</p>
        </div>

        <div className="flex justify-end pt-4">
          <button className="px-6 py-2.5 bg-[#121212] text-white text-sm font-medium rounded-lg hover:bg-black transition-colors shadow-sm">
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  );
};

export default TelephonyView;
