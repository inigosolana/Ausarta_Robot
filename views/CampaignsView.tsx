
import React, { useState } from 'react';
import { Plus, X, Upload, ChevronDown, ChevronRight } from 'lucide-react';

const CampaignsView: React.FC = () => {
  const [isCreating, setIsCreating] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  if (isCreating) {
    return (
      <div className="space-y-6">
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Create Campaign</h1>
            <p className="text-gray-500 text-sm mt-1">Set up a new campaign to execute workflows at scale</p>
          </div>
          <button onClick={() => setIsCreating(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400">
            <X size={20} />
          </button>
        </header>

        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 space-y-6">
          <h3 className="text-base font-bold text-gray-900">Campaign Details</h3>
          <p className="text-xs text-gray-400 -mt-5">Configure your campaign settings</p>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Campaign Name</label>
              <input 
                type="text" 
                placeholder="Enter campaign name" 
                className="w-full h-10 px-4 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              />
              <p className="text-[11px] text-gray-400 mt-1">Choose a descriptive name for your campaign</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Workflow</label>
              <div className="relative">
                <select className="w-full h-10 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer">
                  <option value="">Select a workflow</option>
                  <option>Lead Qualification</option>
                  <option>Customer Feedback</option>
                  <option>Appointment Setting</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
              </div>
              <p className="text-[11px] text-gray-400 mt-1">Select the workflow to execute for each row in the data source</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Data Source Type</label>
              <div className="relative">
                <select className="w-full h-10 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer">
                  <option>CSV File</option>
                  <option>API Webhook</option>
                  <option>Manual Entry</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
              </div>
              <p className="text-[11px] text-gray-400 mt-1">Choose where your contact data is stored</p>
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-semibold text-gray-800">CSV File</label>
              <label className="flex flex-col items-center justify-center w-32 px-4 py-2 bg-white border border-gray-200 rounded-lg shadow-sm cursor-pointer hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700">
                <Upload size={14} className="mb-0 mr-2" />
                Upload CSV
                <input type="file" className="hidden" accept=".csv" />
              </label>
              <p className="text-[11px] text-gray-500 leading-relaxed">
                Upload a CSV file with contact data. Must include <code className="bg-gray-100 px-1 rounded text-red-500 font-normal">phone_number</code> column. The columns can be accessed as initial_context in the workflow nodes.<br/>Max 10MB.
              </p>
            </div>

            <button 
              onClick={() => setAdvancedOpen(!advancedOpen)}
              className="flex items-center justify-between w-full p-4 border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors"
            >
              <span className="text-sm font-bold text-gray-800">Advanced Settings</span>
              <ChevronRight size={18} className={`text-gray-400 transition-transform ${advancedOpen ? 'rotate-90' : ''}`} />
            </button>
          </div>

          <div className="flex gap-3 pt-4">
            <button className="flex-1 py-2.5 bg-gray-400 text-white text-sm font-medium rounded-lg hover:bg-gray-500 transition-colors shadow-sm">
              Create Campaign
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
          <p className="text-gray-500 text-sm mt-1">Manage your bulk workflow execution campaigns</p>
        </div>
        <button 
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#121212] text-white text-sm font-medium rounded-lg hover:bg-black transition-colors shadow-sm"
        >
          <Plus size={18} />
          Create Campaign
        </button>
      </header>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden p-8 flex flex-col items-center justify-center min-h-[400px]">
        <h3 className="text-sm font-bold text-gray-900">All Campaigns</h3>
        <p className="text-xs text-gray-400 mb-12">View and manage your campaigns</p>

        <div className="text-center space-y-4">
          <p className="text-sm text-gray-400 font-medium">No campaigns found</p>
          <button 
            onClick={() => setIsCreating(true)}
            className="flex items-center gap-2 px-4 py-1.5 bg-white border border-gray-200 text-gray-700 text-xs font-semibold rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
          >
            <Plus size={14} />
            Create your first campaign
          </button>
        </div>
      </div>
    </div>
  );
};

export default CampaignsView;
