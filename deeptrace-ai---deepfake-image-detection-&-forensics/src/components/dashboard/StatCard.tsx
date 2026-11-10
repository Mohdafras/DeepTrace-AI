/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: LucideIcon;
  accentColor?: 'cyan' | 'purple' | 'green' | 'rose' | 'amber';
  badgeText?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  accentColor = 'cyan',
  badgeText,
}) => {
  const colorMap = {
    cyan: {
      border: 'border-[#21D4FD]/20 group-hover:border-[#21D4FD]/40',
      iconBg: 'bg-[#21D4FD]/10 text-[#21D4FD] border-[#21D4FD]/30',
      valueColor: 'text-[#21D4FD]',
    },
    purple: {
      border: 'border-[#8B5CF6]/20 group-hover:border-[#8B5CF6]/40',
      iconBg: 'bg-[#8B5CF6]/10 text-[#8B5CF6] border-[#8B5CF6]/30',
      valueColor: 'text-[#8B5CF6]',
    },
    green: {
      border: 'border-[#10B981]/20 group-hover:border-[#10B981]/40',
      iconBg: 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30',
      valueColor: 'text-[#10B981]',
    },
    rose: {
      border: 'border-[#F43F5E]/20 group-hover:border-[#F43F5E]/40',
      iconBg: 'bg-[#F43F5E]/10 text-[#F43F5E] border-[#F43F5E]/30',
      valueColor: 'text-[#F43F5E]',
    },
    amber: {
      border: 'border-[#F59E0B]/20 group-hover:border-[#F59E0B]/40',
      iconBg: 'bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/30',
      valueColor: 'text-[#F59E0B]',
    },
  };

  const scheme = colorMap[accentColor];

  return (
    <div
      className={`group relative p-5 bg-[#111B2D] border rounded-xl transition-all duration-200 ${scheme.border} shadow-lg shadow-black/20`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">{title}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-extrabold text-[#F8FAFC] tracking-tight break-words">
              {value}
            </span>
            {badgeText && (
              <span className="text-[11px] font-medium text-[#94A3B8] font-mono">
                {badgeText}
              </span>
            )}
          </div>
          <p className="mt-1.5 text-xs text-[#94A3B8] flex items-center gap-1.5">
            {subtitle}
          </p>
        </div>

        <div className={`p-2.5 rounded-lg border ${scheme.iconBg}`}>
          <Icon size={20} />
        </div>
      </div>
    </div>
  );
};
