import React from 'react';
import TopicBadge from './TopicBadge';

export default function Dashboard({ stats }) {
  if (!stats) return null;

  const total = stats.total_questions || 0;
  const avgConf = stats.average_confidence || 0;
  const topics = stats.topics || [];

  return (
    <div className="space-y-3">
      {/* Mini Stats Grid */}
      <div className="grid grid-cols-2 gap-2">
        <div className="glass-card p-3 flex flex-col">
          <span className="text-[8px] font-bold text-white/25 uppercase tracking-widest">Total Scans</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-xl font-extrabold text-white/90 text-glow">{total}</span>
            <span className="text-[9px] text-white/20">solved</span>
          </div>
        </div>
        <div className="glass-card p-3 flex flex-col">
          <span className="text-[8px] font-bold text-white/25 uppercase tracking-widest">Avg Accuracy</span>
          <div className="flex items-baseline gap-1 mt-1">
            <span className="text-xl font-extrabold text-emerald-400 text-glow-emerald">{avgConf}%</span>
            <span className="text-[9px] text-white/20">conf.</span>
          </div>
        </div>
      </div>

      {/* Topic breakdown */}
      <div className="glass-card p-3">
        <h4 className="text-[9px] font-bold text-white/25 uppercase tracking-widest mb-2">Topic Breakdown</h4>
        {topics.length === 0 ? (
          <p className="text-[10px] text-white/15 text-center py-2">No data yet</p>
        ) : (
          <div className="space-y-1.5 max-h-[120px] overflow-y-auto pr-0.5">
            {topics.map((t, i) => (
              <div key={i} className="flex items-center justify-between text-[10px]">
                <span className="truncate max-w-[100px]"><TopicBadge topic={t.topic} /></span>
                <span className="font-mono text-white/25">{t.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
