/**
 * HistoryPanel — Compact list of past scan results.
 */
import TopicBadge from './TopicBadge';

export default function HistoryPanel({ history, activeId, onSelect }) {
  if (!history || history.length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-[10px] text-white/20 font-medium">No scan history yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5 max-h-[320px] overflow-y-auto pr-0.5">
      {history.map((item, i) => {
        const isActive = item.id === activeId;
        const correctLabel = (item.correct_answer || '?').toUpperCase();
        return (
          <button
            key={item.id || i}
            onClick={() => onSelect(item)}
            className={`w-full flex items-center gap-2.5 p-2.5 rounded-xl text-left transition-all duration-200 border ${
              isActive
                ? 'bg-indigo-500/10 border-indigo-500/20'
                : 'bg-white/2 border-white/3 hover:bg-white/4 hover:border-white/8'
            }`}
          >
            <span
              className={`flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-[10px] font-extrabold ${
                isActive
                  ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20'
                  : 'bg-white/5 text-white/30'
              }`}
            >
              {correctLabel}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-white/60 font-medium truncate leading-snug">
                {item.question || 'Unknown question'}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[9px] text-white/25">{item.topic || 'General'}</span>
                <span className="text-[9px] text-white/15">·</span>
                <span className="text-[9px] font-mono text-white/20">{item.confidence || 0}%</span>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
