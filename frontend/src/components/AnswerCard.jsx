/**
 * AnswerCard — Glassmorphic on-screen answer display.
 * Shows the correct answer prominently with options, reasoning, and confidence.
 */
import TopicBadge from './TopicBadge';

function ConfidenceBar({ value }) {
  const v = Math.max(0, Math.min(100, value));
  const color =
    v >= 80 ? 'from-emerald-500 to-green-400' :
    v >= 50 ? 'from-amber-500 to-yellow-400' :
              'from-red-500 to-orange-400';
  return (
    <div className="flex items-center gap-2">
      <div className="confidence-bar flex-1">
        <div
          className={`confidence-bar-fill bg-gradient-to-r ${color}`}
          style={{ width: `${v}%` }}
        />
      </div>
      <span className="text-[10px] font-mono font-bold text-white/40 w-8 text-right">
        {v}%
      </span>
    </div>
  );
}

function OptionPill({ label, text, isCorrect }) {
  return (
    <div
      className={`flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all duration-300 ${
        isCorrect
          ? 'option-correct'
          : 'option-wrong opacity-40'
      }`}
    >
      <span
        className={`flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-extrabold ${
          isCorrect
            ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30'
            : 'bg-white/5 text-white/30'
        }`}
      >
        {label}
      </span>
      <span className={`text-xs leading-snug ${isCorrect ? 'text-emerald-200 font-semibold' : 'text-white/30'}`}>
        {text}
      </span>
      {isCorrect && (
        <svg className="w-4 h-4 text-emerald-400 flex-shrink-0 ml-auto" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      )}
    </div>
  );
}

export default function AnswerCard({ result, isLatest = false }) {
  if (!result) return null;

  const options = result.options || [];
  const correctLabel = (result.correct_answer || '').toUpperCase();
  const correctOption = options.find(o => o.label.toUpperCase() === correctLabel);

  return (
    <div className={`space-y-3 animate-slide-up`}>
      {/* ─── Hero Answer ─────────────────────────────────── */}
      <div className="answer-glow p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-xl bg-emerald-500 text-white flex items-center justify-center font-extrabold text-sm shadow-lg shadow-emerald-500/30">
              {correctLabel}
            </span>
            <div>
              <p className="text-[9px] font-semibold text-emerald-400/60 uppercase tracking-widest">Correct Answer</p>
              <p className="text-sm font-bold text-emerald-200 leading-tight">
                {correctOption?.text || result.answer_text || `Option ${correctLabel}`}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-lg font-extrabold text-emerald-400 text-glow-emerald">{result.confidence || 0}%</p>
            <p className="text-[8px] text-emerald-400/40 font-semibold uppercase">Confidence</p>
          </div>
        </div>
        <ConfidenceBar value={result.confidence || 0} />
      </div>

      {/* ─── Meta: Topic + Time ──────────────────────────── */}
      <div className="flex items-center justify-between px-1">
        <TopicBadge topic={result.topic} />
        <div className="flex items-center gap-1.5 text-white/25">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-[10px] font-mono">{result.processing_time_ms}ms</span>
        </div>
      </div>

      {/* ─── Question ────────────────────────────────────── */}
      <div className="glass-card p-3">
        <p className="text-[9px] font-semibold text-indigo-400/50 uppercase tracking-wider mb-1.5">Question</p>
        <p className="text-xs text-white/70 leading-relaxed">
          {result.question || 'Question not detected'}
        </p>
      </div>

      {/* ─── All Options ─────────────────────────────────── */}
      {options.length > 0 && (
        <div className="space-y-1.5">
          {options.map((opt) => (
            <OptionPill
              key={opt.label}
              label={opt.label}
              text={opt.text}
              isCorrect={opt.label.toUpperCase() === correctLabel}
            />
          ))}
        </div>
      )}

      {/* ─── Reasoning ───────────────────────────────────── */}
      {result.reasoning && (
        <div className="glass-card p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <svg className="w-3 h-3 text-indigo-400/60" fill="currentColor" viewBox="0 0 20 20">
              <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM4 11a1 1 0 100-2H3a1 1 0 000 2h1zM10 18a1 1 0 001-1v-1a1 1 0 10-2 0v1a1 1 0 001 1z" />
              <path fillRule="evenodd" d="M10 2a8 8 0 100 16 8 8 0 000-16zm0 14a6 6 0 110-12 6 6 0 010 12z" clipRule="evenodd" />
            </svg>
            <span className="text-[9px] font-bold text-indigo-400/50 uppercase tracking-wider">Reasoning</span>
          </div>
          <p className="text-[11px] text-white/50 leading-relaxed">{result.reasoning}</p>
        </div>
      )}
    </div>
  );
}
