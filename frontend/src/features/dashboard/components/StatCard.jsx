/**
 * StatCard — summary metric tile on the Dashboard.
 * Props: label (string), value (string|number), valueColor (optional CSS color)
 */
export const StatCard = ({ label, value, valueColor }) => (
  <div className="knit-card flex flex-col gap-2 p-5">
    <span className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">
      {label}
    </span>
    <span
      className="font-mono text-3xl leading-none font-normal tabular-nums"
      style={{ color: valueColor ?? 'var(--text)' }}
    >
      {value}
    </span>
  </div>
);

