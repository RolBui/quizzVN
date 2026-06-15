import { useEffect, useMemo, useState } from "react";
import { motion, useSpring, useTransform, type Variants } from "motion/react";
import {
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  ChevronDown,
  MoreHorizontal,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { adminApi, type CrmMetric, type CrmOverview, type CrmPeriod } from "../lib/api";

function Counter({
  value,
  isFloat = false,
  suffix = "",
}: {
  value: number;
  isFloat?: boolean;
  suffix?: string;
}) {
  const spring = useSpring(0, { bounce: 0, duration: 1200 });

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  const display = useTransform(spring, (current) => {
    if (isFloat) {
      return current.toFixed(1) + suffix;
    }
    return Math.round(current).toLocaleString("vi-VN") + suffix;
  });

  return <motion.span>{display}</motion.span>;
}

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

const crmPeriodOptions: { label: string; value: CrmPeriod }[] = [
  { label: "7 ngày qua", value: "7d" },
  { label: "30 ngày qua", value: "30d" },
  { label: "Năm nay", value: "year" },
];

const fallbackOverview: CrmOverview = {
  metrics: [
    {
      key: "total_exams",
      label: "Tổng đề thi",
      value: 0,
      suffix: "",
      trend: "0%",
      is_up: true,
      subtext: "so với tháng trước",
    },
    {
      key: "new_users",
      label: "User mới",
      value: 0,
      suffix: "",
      trend: "0%",
      is_up: true,
      subtext: "so với tháng trước",
    },
    {
      key: "active_users",
      label: "Đang hoạt động",
      value: 0,
      suffix: "",
      trend: "0 phiên",
      is_up: true,
      subtext: "",
    },
    {
      key: "total_users",
      label: "Tổng user",
      value: 0,
      suffix: "",
      trend: "0%",
      is_up: true,
      subtext: "so với tháng trước",
    },
  ],
  traffic: Array.from({ length: 12 }, (_, index) => ({
    name: `T${index + 1}`,
    current: 0,
    last: 0,
  })),
  score_distribution: ["< 5", "5-6", "6-7", "7-8", "8-9", "9-10"].map(
    (name) => ({ name, users: 0 }),
  ),
  recent_results: [],
  last_updated_at: new Date(0).toISOString(),
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function getResultStatusClass(status: string) {
  if (status === "Hoàn thành") {
    return "badge-success";
  }
  if (status === "Cần cải thiện") {
    return "badge-destructive";
  }
  return "badge-warning";
}

const metricSparklineConfig: Record<
  string,
  { stroke: string; fill: string }
> = {
  total_exams: {
    stroke: "#f59e0b",
    fill: "rgba(245, 158, 11, 0.3)",
  },
  new_users: {
    stroke: "#10b981",
    fill: "rgba(16, 185, 129, 0.3)",
  },
  active_users: {
    stroke: "#ec4899",
    fill: "rgba(236, 72, 153, 0.3)",
  },
  total_users: {
    stroke: "#818cf8",
    fill: "rgba(129, 140, 248, 0.32)",
  },
};

const fallbackSparkline = {
  stroke: "#64748b",
  fill: "rgba(100, 116, 139, 0.28)",
};

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
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function MetricCard({ metric }: { metric: CrmMetric }) {
  const TrendIcon = metric.is_up ? ArrowUpRight : ArrowDownRight;
  const sparklineStyle =
    metricSparklineConfig[metric.key] ?? fallbackSparkline;
  const sparklineValues =
    metric.sparkline && metric.sparkline.length >= 2
      ? metric.sparkline
      : [metric.value, metric.value];

  return (
    <motion.div
      variants={itemVariants}
      className="bg-surface-container-lowest rounded-lg p-4 border border-surface-variant shadow-(--shadow-level-1) flex flex-col justify-between min-h-33"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-on-surface font-semibold text-sm truncate">
            {metric.label}
          </p>
          <h3 className="text-2xl font-bold text-on-surface mt-3">
            <Counter value={metric.value} suffix={metric.suffix} />
          </h3>
        </div>
        <MetricSparkline values={sparklineValues} {...sparklineStyle} />
      </div>
      <div className="flex items-center gap-2 mt-3">
        <div
          className={`flex items-center gap-1 text-xs font-semibold tracking-wide ${
            metric.is_up ? "text-emerald-500" : "text-red-500"
          }`}
        >
          <TrendIcon className="w-3.5 h-3.5" />
          {metric.trend}
        </div>
        {metric.subtext && (
          <span className="text-xs text-on-surface-variant font-medium truncate">
            {metric.subtext}
          </span>
        )}
      </div>
    </motion.div>
  );
}

export function Dashboard() {
  const [overview, setOverview] = useState<CrmOverview | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<CrmPeriod>("7d");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    adminApi
      .getCrmOverview(selectedPeriod)
      .then((data) => {
        if (!isMounted) {
          return;
        }
        setOverview(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!isMounted) {
          return;
        }
        setError(
          err instanceof Error ? err.message : "Không lấy được dữ liệu CRM",
        );
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedPeriod]);

  const data = overview ?? fallbackOverview;
  const selectedPeriodLabel =
    crmPeriodOptions.find((option) => option.value === selectedPeriod)?.label ??
    "7 ngày qua";
  const trafficSubtitle =
    selectedPeriod === "year"
      ? "Số lượt bắt đầu bài thi theo tháng"
      : selectedPeriod === "30d"
        ? "Số lượt bắt đầu bài thi theo ngày (30 ngày)"
        : "Số lượt bắt đầu bài thi theo ngày (7 ngày)";
  const trafficCurrentLabel =
    selectedPeriod === "year" ? "Năm nay" : "Kỳ hiện tại";
  const trafficLastLabel =
    selectedPeriod === "year" ? "Năm ngoái" : "Kỳ trước";
  const scoreDistributionTitle =
    selectedPeriod === "year"
      ? "Phổ điểm năm nay"
      : selectedPeriod === "30d"
        ? "Phổ điểm 30 ngày"
        : "Phổ điểm tuần";
  const scoreEmptyText =
    selectedPeriod === "year"
      ? "Chưa có dữ liệu năm nay"
      : selectedPeriod === "30d"
        ? "Chưa có dữ liệu 30 ngày qua"
        : "Chưa có dữ liệu tuần này";
  const topScoreBucket = useMemo(() => {
    return [...data.score_distribution].sort((a, b) => b.users - a.users)[0];
  }, [data.score_distribution]);
  const totalScoreUsers = useMemo(() => {
    return data.score_distribution.reduce(
      (total, bucket) => total + bucket.users,
      0,
    );
  }, [data.score_distribution]);
  const topScorePercent =
    topScoreBucket && totalScoreUsers > 0
      ? Math.round((topScoreBucket.users / totalScoreUsers) * 100)
      : 0;

  return (
    <div className="p-4 flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-lg font-semibold text-on-surface">Bảng điều khiển</h1>
        </div>
        <div className="relative w-full sm:w-36">
          <select
            value={selectedPeriod}
            onChange={(event) =>
              setSelectedPeriod(event.target.value as CrmPeriod)
            }
            className="w-full appearance-none bg-surface-container-lowest border border-surface-variant text-sm py-2 pl-4 pr-10 rounded-lg focus:outline-none focus:border-primary cursor-pointer text-on-surface"
          >
            {crmPeriodOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-on-surface">
          <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Chưa lấy được dữ liệu CRM</p>
            <p className="text-on-surface-variant">{error}</p>
          </div>
        </div>
      )}

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4"
      >
        {isLoading
          ? fallbackOverview.metrics.map((metric) => (
              <div
                key={metric.key}
                className="bg-surface-container-lowest rounded-lg p-4 border border-surface-variant shadow-(--shadow-level-1) min-h-33 animate-pulse"
              >
                <div className="h-4 w-24 rounded bg-surface-container-high" />
                <div className="h-8 w-20 rounded bg-surface-container-high mt-3" />
                <div className="h-10 w-32 rounded bg-surface-container-high mt-3 ml-auto" />
                <div className="h-4 w-36 rounded bg-surface-container-high mt-3" />
              </div>
            ))
          : data.metrics.map((metric) => (
              <MetricCard key={metric.key} metric={metric} />
            ))}
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 bg-surface-container-lowest rounded-xl p-4 sm:p-5 border border-surface-variant shadow-(--shadow-level-1)">
          <div className="flex flex-col items-start mb-4 gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-on-surface">
                Lưu lượng làm bài
              </h2>
              <p className="text-sm text-on-surface-variant mt-1">
                {trafficSubtitle}
              </p>
            </div>
            <span className="bg-surface-container text-sm py-1.5 px-3 rounded-lg text-on-surface font-medium">
              {selectedPeriodLabel}
            </span>
          </div>
          <div className="h-56 w-full sm:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={data.traffic}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorCurrent" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="5%"
                      stopColor="var(--color-primary)"
                      stopOpacity={0.2}
                    />
                    <stop
                      offset="95%"
                      stopColor="var(--color-primary)"
                      stopOpacity={0}
                    />
                  </linearGradient>
                  <linearGradient id="colorLast" x1="0" y1="0" x2="0" y2="1">
                    <stop
                      offset="5%"
                      stopColor="var(--color-outline-variant)"
                      stopOpacity={0.2}
                    />
                    <stop
                      offset="95%"
                      stopColor="var(--color-outline-variant)"
                      stopOpacity={0}
                    />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="var(--color-surface-variant)"
                />
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "var(--color-outline)", fontSize: 12 }}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "var(--color-outline)", fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: "8px",
                    border: "none",
                    boxShadow: "var(--shadow-level-2)",
                    backgroundColor: "var(--color-surface-container-lowest)",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="last"
                  name={trafficLastLabel}
                  stroke="var(--color-outline)"
                  fillOpacity={1}
                  fill="url(#colorLast)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="current"
                  name={trafficCurrentLabel}
                  stroke="var(--color-primary)"
                  fillOpacity={1}
                  fill="url(#colorCurrent)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="xl:col-span-1 bg-surface-container-lowest rounded-xl p-4 sm:p-5 shadow-(--shadow-level-1) flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-on-surface">{scoreDistributionTitle}</h3>
            <button className="text-outline hover:text-on-surface">
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>
          <div className="h-40 w-full mb-4 mt-2 sm:h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data.score_distribution}
                margin={{ top: 0, right: 0, left: -20, bottom: 0 }}
                barSize={32}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="var(--color-surface-variant)"
                />
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "var(--color-outline)", fontSize: 12 }}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "var(--color-outline)", fontSize: 12 }}
                />
                <Tooltip
                  cursor={{ fill: "var(--color-surface-container)" }}
                  contentStyle={{
                    borderRadius: "8px",
                    border: "none",
                    boxShadow: "var(--shadow-level-1)",
                    backgroundColor: "var(--color-surface-container-lowest)",
                  }}
                />
                <Bar
                  dataKey="users"
                  name="Số học sinh"
                  fill="var(--color-primary)"
                  radius={[4, 4, 4, 4]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-auto">
            <div className="flex items-center justify-between py-3 border-t border-surface-variant gap-4">
              <div>
                <p className="text-sm font-semibold text-on-surface">
                  Phổ điểm nhiều nhất
                </p>
                <p className="text-xs text-outline">
                  {topScoreBucket && totalScoreUsers > 0
                    ? `${topScoreBucket.name} điểm (${topScoreBucket.users} học sinh)`
                    : scoreEmptyText}
                </p>
              </div>
              <div className="px-2.5 py-1 bg-primary-fixed text-on-primary-fixed text-xs font-semibold rounded-md">
                {topScorePercent}%
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) overflow-hidden">
        <div className="p-5 border-b border-surface-variant flex justify-between items-center">
          <h3 className="text-lg font-bold text-on-surface">
            Kết quả thi mới nhất
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low/30 border-b border-surface-variant">
                <th className="py-4 px-6 text-xs font-semibold text-outline uppercase tracking-wider">
                  Mã bài thi
                </th>
                <th className="py-4 px-6 text-xs font-semibold text-outline uppercase tracking-wider">
                  Học sinh
                </th>
                <th className="py-4 px-6 text-xs font-semibold text-outline uppercase tracking-wider">
                  Kỳ thi
                </th>
                <th className="py-4 px-6 text-xs font-semibold text-outline uppercase tracking-wider">
                  Ngày nộp
                </th>
                <th className="py-4 px-6 text-xs font-semibold text-outline uppercase tracking-wider">
                  Điểm số
                </th>
                <th className="py-4 px-6 text-xs font-semibold text-outline uppercase tracking-wider">
                  Đánh giá
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-variant">
              {data.recent_results.length > 0 ? (
                data.recent_results.map((result) => (
                  <tr
                    key={result.attempt_id}
                    className="hover:bg-surface-container-low/30 transition-colors"
                  >
                    <td className="py-4 px-6 text-sm font-medium text-primary">
                      {result.code}
                    </td>
                    <td className="py-4 px-6 text-sm font-semibold text-on-surface">
                      {result.student_name}
                    </td>
                    <td className="py-4 px-6 text-sm text-outline">
                      {result.exam_title}
                    </td>
                    <td className="py-4 px-6 text-sm text-outline">
                      {formatDate(result.submitted_at)}
                    </td>
                    <td className="py-4 px-6 text-sm font-medium text-on-surface">
                      {result.score_label}
                    </td>
                    <td className="py-4 px-6">
                      <span
                        className={`badge ${getResultStatusClass(result.status)}`}
                      >
                        {result.status}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={6}
                    className="py-8 px-6 text-center text-sm text-on-surface-variant"
                  >
                    Chưa có kết quả thi
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
