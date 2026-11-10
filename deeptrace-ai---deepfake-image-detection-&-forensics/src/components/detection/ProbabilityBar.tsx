import { ShieldCheck, AlertTriangle } from 'lucide-react';
import { formatScore } from '../../utils';

export function ProbabilityBar({ realProbability, fakeProbability, confidence, threshold }: {
  realProbability: number; fakeProbability: number; confidence: number; threshold: number | null;
}) {
  const scores = [
    { label: 'Real score', value: realProbability, color: '#059669', Icon: ShieldCheck },
    { label: 'Fake score', value: fakeProbability, color: '#F43F5E', Icon: AlertTriangle },
  ];
  return <div className="space-y-4">
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{scores.map(({ label, value, color, Icon }) => <div key={label} className="p-3 bg-[#080D18] border border-[#243247] rounded-lg min-w-0">
      <div className="flex items-center justify-between gap-3 text-xs mb-2"><span className="flex items-center gap-2"><Icon size={15} style={{ color }} />{label}</span><span className="font-mono font-bold text-sm">{formatScore(value)}</span></div>
      <div role="meter" tabIndex={0} title={`${label}: ${(value * 100).toFixed(2)}%`} aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value * 100} className="h-2 bg-[#152238] rounded-full overflow-hidden"><div style={{ width: `${value * 100}%`, background: color }} className="h-full rounded-full" /></div>
      <p className="font-mono text-[11px] text-[#94A3B8] mt-2">{value.toFixed(4)}</p>
    </div>)}</div>
    <div className="p-3 bg-[#080D18] border border-[#243247] rounded-lg text-xs space-y-2"><p className="flex flex-wrap justify-between gap-2"><span>Model confidence score: <strong>{formatScore(confidence)}</strong></span><span>Real-score threshold: <strong>{threshold === null ? 'Not recorded' : threshold}</strong></span></p><p className="text-[#94A3B8]">The server predicts REAL when its real score is at or above the configured threshold. Scores are not calibrated probabilities of correctness.</p></div>
  </div>;
}
