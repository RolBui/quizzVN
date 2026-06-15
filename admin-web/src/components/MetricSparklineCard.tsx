import { ArrowDownRight, ArrowUpRight } from "lucide-react";

interface SparklinePalette {
  stroke: string;
  fill: string;
}

interface MetricSparklineCardProps {
  label: string;
  value: string;
  trend: string;
  isUp: boolean;
  subtext?: string;
  sparkline?: number[];
  palette: SparklinePalette;
}

function buildSmoothPath(points: { x: number; y: number }[]) {
  if (points.length === 0) {
    return "";
  }

  return points.reduce((path, point, index) => {
    if (index === 0) {
      return `M ${point.x} ${point.y}`;
    }

    const previous = points[index - 1];
    const controlX = (previous.x + point.x) / 2;
    return `${path} C ${controlX} ${previous.y}, ${controlX} ${point.y}, ${point.x} ${point.y}`;
  }, "");
}

function MetricSparkline({
  values,
  stroke,
  fill,
}: {
  values: number[];
  stroke: string;
  fill: string;
}) {
  const width = 132;
  const height = 54;
  const padding = 5;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min;
  const points = values.map((value, index) => {
    const x = padding + (index / (values.length - 1)) * (width - padding * 2);
    const y =
      range === 0
        ? height / 2
        : height - padding - ((value - min) / range) * (height - padding * 2);
    return { x, y };
  });
  const linePath = buildSmoothPath(points);
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${
    height - padding
  } L ${points[0].x} ${height - padding} Z`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-14 w-32 shrink-0"
      aria-hidden="true"
    >
      <path d={areaPath} fill={fill} />
      <path
        d={linePath}
        fill="none"
        stroke={stroke}
        strokeWidth={2.8}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function MetricSparklineCard({
  label,
  value,
  trend,
  isUp,
  subtext,
  sparkline,
  palette,
}: MetricSparklineCardProps) {
  const TrendIcon = isUp ? ArrowUpRight : ArrowDownRight;
  const values =
    sparkline && sparkline.length >= 2
      ? sparkline
      : [Number(value) || 0, Number(value) || 0];

  return (
    <div className="bg-surface-container-lowest rounded-lg p-4 border border-surface-variant shadow-(--shadow-level-1) flex flex-col justify-between min-h-33">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-on-surface font-semibold text-sm truncate">
            {label}
          </p>
          <p className="text-2xl font-bold text-on-surface mt-3">{value}</p>
        </div>
        <MetricSparkline values={values} {...palette} />
      </div>
      <div className="flex items-center gap-2 mt-3">
        <div
          className={`flex items-center gap-1 text-xs font-semibold tracking-wide ${
            isUp ? "text-emerald-500" : "text-red-500"
          }`}
        >
          <TrendIcon className="w-3.5 h-3.5" />
          {trend}
        </div>
        {subtext && (
          <span className="text-xs text-on-surface-variant font-medium truncate">
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
}
