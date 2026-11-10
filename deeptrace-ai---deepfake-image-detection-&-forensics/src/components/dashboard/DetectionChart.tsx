import { useState } from 'react';
import { ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { BarChart3, ShieldCheck, AlertTriangle } from 'lucide-react';
import type { DetectionRecord } from '../../types';
import { formatScore } from '../../utils';

// Validated against #111B2D: all palette checks pass, worst CVD separation 8.3.
const REAL_MARK = '#059669';
const FAKE_MARK = '#F43F5E';
const tooltipStyle = { backgroundColor: '#0B1220', border: '1px solid #243247', borderRadius: '8px', color: '#F8FAFC', fontSize: '12px' };

export function DetectionChart({ history }: { history: DetectionRecord[] }) {
  const [table, setTable] = useState(false);
  const realCount = history.filter(record => record.prediction === 'REAL').length;
  const fakeCount = history.length - realCount;
  const distribution = [
    { name: 'Predicted REAL', value: realCount, color: REAL_MARK, Icon: ShieldCheck },
    { name: 'Predicted FAKE', value: fakeCount, color: FAKE_MARK, Icon: AlertTriangle },
  ];
  const recent = [...history].sort((a, b) => b.id - a.id).slice(0, 10).reverse();
  const data = recent.map(record => ({ name: `#${record.id}`, confidence: Number((record.confidence * 100).toFixed(1)), filename: record.filename }));
  return <div className="space-y-3">
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <section className="panel chart-panel">
        <div className="flex flex-wrap gap-2 justify-between border-b border-[#243247] pb-3">
          <h3 className="text-sm font-semibold flex items-center gap-2"><BarChart3 size={17} className="text-[#21D4FD]" />Classification Distribution</h3>
          <span className="text-xs text-[#94A3B8]">{history.length} records</span>
        </div>
        {!history.length ? <p className="text-center py-16 text-xs text-[#94A3B8]">No analysis data in this view.</p> :
          <div className="space-y-7 py-6" aria-label="Classification counts">
            {distribution.map(({ name, value, color, Icon }) => <div key={name}>
              <div className="flex items-center justify-between gap-3 text-xs mb-3">
                <span className="flex items-center gap-2"><Icon size={16} style={{ color }} />{name}</span>
                <span>{value} records · {(value / history.length * 100).toFixed(1)}%</span>
              </div>
              <div role="meter" tabIndex={0} aria-label={name} aria-valuemin={0} aria-valuemax={history.length} aria-valuenow={value}
                title={`${name}: ${value} of ${history.length}`} className="h-3 rounded-r bg-[#152238]">
                <div className="h-full rounded-r" style={{ width: `${value / history.length * 100}%`, backgroundColor: color }} />
              </div>
            </div>)}
          </div>}
      </section>
      <section className="panel chart-panel">
        <div className="flex flex-wrap gap-2 justify-between border-b border-[#243247] pb-3">
          <h3 className="text-sm font-semibold flex items-center gap-2"><BarChart3 size={17} className="text-[#8B5CF6]" />Recent Confidence Overview</h3>
          <span className="text-xs text-[#94A3B8]">Last 10 inferences</span>
        </div>
        {!data.length ? <p className="text-center py-16 text-xs text-[#94A3B8]">No confidence scores in this view.</p> :
          <div className="h-56 pt-4" aria-label="Model confidence scores for the latest ten records">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 4 }} accessibilityLayer>
                <CartesianGrid stroke="#243247" vertical={false} />
                <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={{ stroke: '#243247' }} />
                <YAxis domain={[0, 100]} stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} tickFormatter={value => `${value}%`} />
                <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#F8FAFC' }} cursor={{ fill: '#21D4FD0d' }} formatter={value => [`${value}%`, 'Model confidence']} />
                <Bar dataKey="confidence" fill="#2a78d6" radius={[4, 4, 0, 0]} maxBarSize={24} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>}
        <p className="text-[11px] text-[#94A3B8] mt-2">Confidence is a model score, not measured accuracy.</p>
      </section>
    </div>
    <button className="text-xs text-[#21D4FD] underline underline-offset-4" onClick={() => setTable(value => !value)} aria-expanded={table} aria-controls="chart-data">{table ? 'Hide chart data table' : 'View chart data table'}</button>
    <div id="chart-data" className={`chart-data ${table ? 'panel overflow-x-auto' : 'sr-only'}`}>
      <table className="text-xs w-full text-left"><caption className="text-left mb-3">Distribution: {realCount} predicted REAL, {fakeCount} predicted FAKE. Latest model scores below.</caption>
        <thead><tr><th className="p-2">Record</th><th className="p-2">Filename</th><th className="p-2">Prediction</th><th className="p-2">Confidence score</th></tr></thead>
        <tbody>{recent.map(record => <tr key={record.id}><td className="p-2">#{record.id}</td><td className="p-2 break-all">{record.filename}</td><td className="p-2">{record.prediction}</td><td className="p-2">{formatScore(record.confidence)}</td></tr>)}</tbody>
      </table>
    </div>
  </div>;
}
