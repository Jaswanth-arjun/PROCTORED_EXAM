/**
 * TopicBadge — Compact topic label with color coding.
 */
const TOPIC_COLORS = {
  'DSA':            { bg: 'rgba(99, 102, 241, 0.12)', text: '#818cf8', border: 'rgba(99, 102, 241, 0.2)' },
  'DBMS':           { bg: 'rgba(6, 182, 212, 0.12)', text: '#22d3ee', border: 'rgba(6, 182, 212, 0.2)' },
  'CN':             { bg: 'rgba(16, 185, 129, 0.12)', text: '#34d399', border: 'rgba(16, 185, 129, 0.2)' },
  'OS':             { bg: 'rgba(245, 158, 11, 0.12)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.2)' },
  'React':          { bg: 'rgba(56, 189, 248, 0.12)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.2)' },
  'Java':           { bg: 'rgba(239, 68, 68, 0.12)', text: '#f87171', border: 'rgba(239, 68, 68, 0.2)' },
  'Spring Boot':    { bg: 'rgba(34, 197, 94, 0.12)', text: '#4ade80', border: 'rgba(34, 197, 94, 0.2)' },
  'System Design':  { bg: 'rgba(168, 85, 247, 0.12)', text: '#c084fc', border: 'rgba(168, 85, 247, 0.2)' },
  'Aptitude':       { bg: 'rgba(251, 146, 60, 0.12)', text: '#fb923c', border: 'rgba(251, 146, 60, 0.2)' },
  'Mathematics':    { bg: 'rgba(236, 72, 153, 0.12)', text: '#f472b6', border: 'rgba(236, 72, 153, 0.2)' },
};

const DEFAULT_COLOR = { bg: 'rgba(148, 163, 184, 0.08)', text: '#94a3b8', border: 'rgba(148, 163, 184, 0.15)' };

export default function TopicBadge({ topic }) {
  if (!topic) return null;

  // Find matching color (case-insensitive partial match)
  const key = Object.keys(TOPIC_COLORS).find(k =>
    topic.toLowerCase().includes(k.toLowerCase())
  );
  const colors = key ? TOPIC_COLORS[key] : DEFAULT_COLOR;

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider"
      style={{
        background: colors.bg,
        color: colors.text,
        border: `1px solid ${colors.border}`,
      }}
    >
      {topic}
    </span>
  );
}
