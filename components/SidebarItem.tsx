
import React from 'react';

interface SidebarItemProps {
  icon: React.ReactNode;
  label: string;
  isActive?: boolean;
  onClick: () => void;
  collapsed?: boolean;
}

const SidebarItem: React.FC<SidebarItemProps> = ({ icon, label, isActive, onClick, collapsed }) => {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-3 w-full px-3 py-2 text-sm rounded-lg transition-all duration-200
        ${isActive 
          ? 'bg-gray-100 text-gray-900 font-medium' 
          : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
        }
        ${collapsed ? 'justify-center' : 'justify-start'}
      `}
      title={collapsed ? label : undefined}
    >
      <span className={`${isActive ? 'text-gray-900' : 'text-gray-400'}`}>
        {icon}
      </span>
      {!collapsed && <span>{label}</span>}
    </button>
  );
};

export default SidebarItem;
