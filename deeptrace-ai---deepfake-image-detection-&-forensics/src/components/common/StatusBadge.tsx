/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { ShieldCheck, AlertTriangle } from 'lucide-react';
import { PredictionLabel } from '../../types';

interface StatusBadgeProps {
  prediction: PredictionLabel;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  prediction,
  size = 'md',
  showIcon = true,
}) => {
  const isReal = prediction === 'REAL';

  const sizeClasses = {
    sm: 'text-xs py-0.5 px-2 gap-1',
    md: 'text-xs py-1 px-2.5 gap-1.5',
    lg: 'text-sm py-1.5 px-3 gap-2 font-semibold',
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  if (isReal) {
    return (
      <span
        className={`inline-flex items-center font-medium rounded-md border border-[#10B981]/30 bg-[#10B981]/10 text-[#10B981] ${sizeClasses[size]}`}
      >
        {showIcon && <ShieldCheck size={iconSizes[size]} className="shrink-0 text-[#10B981]" />}
        <span>PREDICTED REAL</span>
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center font-medium rounded-md border border-[#F43F5E]/30 bg-[#F43F5E]/10 text-[#F43F5E] ${sizeClasses[size]}`}
    >
      {showIcon && <AlertTriangle size={iconSizes[size]} className="shrink-0 text-[#F43F5E]" />}
      <span>PREDICTED FAKE</span>
    </span>
  );
};
