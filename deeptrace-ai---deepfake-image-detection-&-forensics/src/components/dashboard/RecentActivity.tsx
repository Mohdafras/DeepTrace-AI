/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { ArrowUpRight, Clock, FileImage, ShieldAlert } from 'lucide-react';
import { DetectionRecord } from '../../types';
import { StatusBadge } from '../common/StatusBadge';

interface RecentActivityProps {
  history: DetectionRecord[];
  onSelectRecord: (record: DetectionRecord) => void;
  onViewAll: () => void;
  disabled?: boolean;
}

export const RecentActivity: React.FC<RecentActivityProps> = ({
  history,
  onSelectRecord,
  onViewAll,
  disabled = false,
}) => {
  const recentRecords = history.slice(0, 5);

  return (
    <div className="bg-[#111B2D] border border-[#243247] rounded-xl overflow-hidden shadow-lg shadow-black/20">
      {/* Table Header Controls */}
      <div className="p-5 border-b border-[#243247] flex flex-wrap gap-3 items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#F8FAFC]">Recent Forensic Activity</h3>
          <p className="text-xs text-[#94A3B8]">Latest deep learning inferences from the FastAPI backend</p>
        </div>

        <button
          onClick={onViewAll}
          className="text-xs text-[#21D4FD] hover:text-[#21D4FD]/80 font-medium flex items-center gap-1 transition-colors"
        >
          <span>View All History</span>
          <ArrowUpRight size={14} />
        </button>
      </div>

      {recentRecords.length === 0 ? (
        <div className="py-12 px-4 text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[#152238] flex items-center justify-center text-[#94A3B8]">
            <Clock size={20} />
          </div>
          <p className="text-xs font-semibold text-[#F8FAFC]">No Analysis History Recorded</p>
          <p className="text-[11px] text-[#94A3B8] max-w-sm mx-auto mt-1">
            When you analyze images through the Image Forensics workspace, the detection outcomes and Grad-CAM logs will be recorded here.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#080D18]/70 text-[#94A3B8] uppercase text-[10px] tracking-wider border-b border-[#243247]">
              <tr>
                <th className="py-3 px-5">Image File</th>
                <th className="py-3 px-5">Prediction</th>
                <th className="py-3 px-5 text-right">Confidence</th>
                <th className="py-3 px-5">Timestamp</th>
                <th className="py-3 px-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#243247]/60 text-[#F8FAFC]">
              {recentRecords.map((record) => {
                const date = new Date(record.timestamp);
                const formattedDate = isNaN(date.getTime())
                  ? record.timestamp
                  : `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

                return (
                  <tr
                    key={record.id}
                    className="hover:bg-[#152238]/60 transition-colors group"
                  >
                    <td className="py-3.5 px-5 font-medium flex items-center gap-2.5 max-w-[200px] truncate">
                      <div className="p-1.5 bg-[#080D18] rounded border border-[#243247] text-[#94A3B8] shrink-0">
                        <FileImage size={14} />
                      </div>
                      <span className="truncate" title={record.filename}>
                        {record.filename}
                      </span>
                    </td>

                    <td className="py-3.5 px-5 whitespace-nowrap">
                      <StatusBadge prediction={record.prediction} size="sm" />
                    </td>

                    <td className="py-3.5 px-5 text-right font-mono font-semibold tabular-nums whitespace-nowrap">
                      <span
                        className={
                          record.prediction === 'REAL' ? 'text-[#10B981]' : 'text-[#F43F5E]'
                        }
                      >
                        {Math.round(record.confidence * 100)}%
                      </span>
                    </td>

                    <td className="py-3.5 px-5 text-[#94A3B8] whitespace-nowrap font-mono text-[11px] tabular-nums">
                      {formattedDate}
                    </td>

                    <td className="py-3.5 px-5 text-right whitespace-nowrap">
                      <button
                        disabled={disabled}
                        onClick={() => onSelectRecord(record)}
                        className="px-2.5 py-1 bg-[#152238] hover:bg-[#21D4FD] text-[#F8FAFC] hover:text-[#080D18] border border-[#243247] hover:border-[#21D4FD] rounded text-[11px] font-medium transition-all"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
