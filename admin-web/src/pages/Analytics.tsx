import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  ChevronDown,
  Monitor,
  Smartphone,
  Tablet,
} from "lucide-react";
import {
  adminApi,
  type AnalyticsBreakdownItem,
  type AnalyticsMetric,
  type AnalyticsOverview,
  type AnalyticsPeriod,
  type AnalyticsRealtime,
  type PaymentAnalyticsOverview,
} from "../lib/api";

const emptyRealtime: AnalyticsRealtime = {
  active_users: 0,
  active_sessions: 0,
  active_pages: [],
  active_window_seconds: 90,
  last_updated_at: new Date(0).toISOString(),
};

const emptyOverview: AnalyticsOverview = {
  metrics: [],
  traffic: [],
  devices: [],
  sources: [],
  popular_pages: [],
  realtime: emptyRealtime,
  last_updated_at: new Date(0).toISOString(),
};

const emptyPaymentOverview: PaymentAnalyticsOverview = {
  metrics: [],
  cash_flow: [],
  paid_orders: 0,
  last_updated_at: new Date(0).toISOString(),
};

const periodOptions: { label: string; value: AnalyticsPeriod }[] = [
  { label: "7 ngày qua", value: "7d" },
  { label: "30 ngày qua", value: "30d" },
  { label: "Năm nay", value: "year" },
];

const kpiOrder = [
  "unique_visitors",
  "page_views",
  "revenue",
  "average_order_value",
] as const;

const kpiCopy: Record<
  string,
  { title: string; unit: string; subtext?: string }
> = {
  unique_visitors: {
    title: "Lưu lượng truy cập",
    unit: "Người",
  },
  page_views: {
    title: "Lượt xem trang",
    unit: "Lượt",
  },
  revenue: {
    title: "Doanh thu",
    unit: "VNĐ",
  },
  average_order_value: {
    title: "Giá trị trung bình đơn",
    unit: "VNĐ",
  },
};

const deviceConfig: Record<
  string,
  { label: string; color: string; icon: typeof Monitor }
> = {
  desktop: { label: "Desktop", color: "#4F46E5", icon: Monitor },
  mobile: { label: "Mobile", color: "#10B981", icon: Smartphone },
  tablet: { label: "Tablet", color: "#F59E0B", icon: Tablet },
};

const sourceLabels: Record<string, string> = {
  direct: "Trực tiếp",
  internal: "website",
  search: "Tìm kiếm",
  social: "Mạng xã hội",
};
const sourceOrder = Object.keys(sourceLabels);

function formatMetricValue(key: string, value: number) {
  return Math.round(value).toLocaleString("vi-VN");
}

function formatChartMoney(value: number) {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toLocaleString("vi-VN", {
      maximumFractionDigits: 1,
    })} tỷ`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("vi-VN", {
      maximumFractionDigits: 1,
    })} tr`;
  }
  if (value >= 1_000) {
    return `${Math.round(value / 1_000).toLocaleString("vi-VN")}k`;
  }
  return value.toLocaleString("vi-VN");
}

function metricByKey(metrics: AnalyticsMetric[], key: string) {
  return metrics.find((metric) => metric.key === key);
}

function normalizedBreakdown(
  items: AnalyticsBreakdownItem[],
  labels: Record<string, string>,
) {
  return items.map((item) => ({
    ...item,
    label: labels[item.name] ?? item.name,
  }));
}

function normalizedSourceBreakdown(items: AnalyticsBreakdownItem[]) {
  const valuesByName = new Map(items.map((item) => [item.name, item.value]));
  const knownSources = sourceOrder.map((name) => ({
    name,
    value: valuesByName.get(name) ?? 0,
    label: sourceLabels[name] ?? name,
  }));
  const extraSources = items
    .filter((item) => item.name !== "unknown" && !sourceLabels[item.name])
    .map((item) => ({
      ...item,
      label: item.name,
    }));

  return [...knownSources, ...extraSources];
}

export function Analytics() {
  const [overview, setOverview] = useState<AnalyticsOverview>(emptyOverview);
  const [paymentOverview, setPaymentOverview] =
    useState<PaymentAnalyticsOverview>(emptyPaymentOverview);
  const [selectedPeriod, setSelectedPeriod] = useState<AnalyticsPeriod>("7d");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    Promise.all([
      adminApi.getAnalyticsTraffic(selectedPeriod),
      adminApi.getAnalyticsPayments(selectedPeriod),
    ])
      .then(([trafficResponse, paymentResponse]) => {
        if (!isMounted) {
          return;
        }
        setOverview(trafficResponse);
        setPaymentOverview(paymentResponse);
      })
      .catch((err: unknown) => {
        if (!isMounted) {
          return;
        }
        setOverview(emptyOverview);
        setPaymentOverview(emptyPaymentOverview);
        setError(
          err instanceof Error
            ? err.message
            : "Không lấy được dữ liệu analytics.",
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

  const kpiData = useMemo(() => {
    return kpiOrder.map((key) => {
      const metric = metricByKey(
        key === "revenue" || key === "average_order_value"
          ? paymentOverview.metrics
          : overview.metrics,
        key,
      );
      const copy = kpiCopy[key];
      const value = Number(metric?.value ?? 0);

      return {
        key,
        title: copy.title,
        value: formatMetricValue(key, value),
        unit: metric?.suffix || copy.unit,
        change: metric?.trend || "0%",
        isPositive: metric?.is_up ?? true,
        subtext: metric?.subtext || copy.subtext || "",
      };
    });
  }, [overview.metrics, paymentOverview.metrics]);

  const trafficData = overview.traffic;
  const deviceData = useMemo(() => {
    return overview.devices.map((item) => {
      const config = deviceConfig[item.name] ?? {
        label: item.name,
        color: "#64748B",
        icon: Monitor,
      };
      return {
        ...item,
        label: config.label,
        color: config.color,
        Icon: config.icon,
      };
    });
  }, [overview.devices]);
  const sourceData = useMemo(
    () => normalizedSourceBreakdown(overview.sources),
    [overview.sources],
  );
  const sourceChartHeight = Math.max(210, sourceData.length * 32 + 28);
  const showSourceChart = !isLoading || overview.sources.length > 0;
  const deviceTotal = deviceData.reduce((total, item) => total + item.value, 0);
  const selectedPeriodLabel =
    periodOptions.find((option) => option.value === selectedPeriod)?.label ??
    "7 ngày qua";
  const currentTrafficLabel =
    selectedPeriod === "year" ? "Năm nay" : "Kỳ hiện tại";
  const lastTrafficLabel = selectedPeriod === "year" ? "Năm ngoái" : "Kỳ trước";
  const hasPaymentData = paymentOverview.cash_flow.some(
    (point) => point.current > 0 || point.last > 0,
  );

  return (
    <div className="p-4 flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-lg font-semibold text-on-surface">
            Phân tích
          </h1>
        </div>
        <div className="flex gap-2">
          <div className="relative w-full sm:w-36">
            <select
              value={selectedPeriod}
              onChange={(event) =>
                setSelectedPeriod(event.target.value as AnalyticsPeriod)
              }
              className="w-full appearance-none bg-surface-container-lowest border border-surface-variant text-sm py-2 pl-4 pr-10 rounded-lg focus:outline-none focus:border-primary cursor-pointer text-on-surface"
            >
              {periodOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-on-surface">
          <AlertCircle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Chưa lấy được dữ liệu analytics</p>
            <p className="text-on-surface-variant">{error}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {kpiData.map((kpi) => {
          const TrendIcon = kpi.isPositive ? ArrowUpRight : ArrowDownRight;
          return (
            <div
              key={kpi.key}
              className="bg-surface-container-lowest rounded-xl border border-surface-variant shadow-(--shadow-level-1) flex flex-col"
            >
              <div className="flex justify-between items-start p-4 gap-3">
                <p className="text-on-surface text-base leading-tight whitespace-pre-line font-medium">
                  {kpi.title}
                </p>
                <span
                  className={`inline-flex items-center gap-1 text-sm font-semibold tracking-wide ${
                    kpi.isPositive ? "text-emerald-500" : "text-red-500"
                  }`}
                >
                  <TrendIcon className="w-3.5 h-3.5" />
                  {kpi.change}
                </span>
              </div>
              <div className="p-4 flex flex-col flex-1">
                <h3 className="text-xl leading-none mb-2 text-on-surface flex items-baseline gap-1.5">
                  <span className="font-semibold">{kpi.value}</span>
                  <span className="text-sm font-normal">{kpi.unit}</span>
                </h3>
                {kpi.subtext && (
                  <p className="text-xs text-outline mb-3">{kpi.subtext}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="bg-surface-container-lowest p-4 sm:p-5 rounded-lg border border-surface-variant shadow-(--shadow-level-1)">
        <div className="flex flex-col items-start gap-3 mb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-bold text-on-surface">
              Dòng tiền thanh toán
            </h3>
            <p className="mt-1 text-xs text-outline">
              Chỉ ghi nhận các đơn đã thanh toán thành công.
            </p>
          </div>
          <span className="bg-surface-container text-sm py-1.5 px-3 rounded-md text-on-surface font-medium">
            {paymentOverview.paid_orders.toLocaleString("vi-VN")} đơn thành công
          </span>
        </div>
        <div className="h-64 w-full sm:h-75">
          {hasPaymentData ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={paymentOverview.cash_flow}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="5 5"
                  vertical={false}
                  stroke="var(--color-surface-variant)"
                />
                <XAxis
                  dataKey="name"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: "var(--color-outline)" }}
                  dy={10}
                />
                <YAxis
                  allowDecimals={false}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: "var(--color-outline)" }}
                  tickFormatter={(value) => formatChartMoney(Number(value))}
                />
                <Tooltip
                  formatter={(value, name) => [
                    `${Math.round(Number(value ?? 0)).toLocaleString("vi-VN")} VNĐ`,
                    String(name ?? ""),
                  ]}
                  contentStyle={{
                    borderRadius: "8px",
                    border: "none",
                    boxShadow: "var(--shadow-level-2)",
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
                  iconType="square"
                />
                <Bar
                  name={lastTrafficLabel}
                  dataKey="last"
                  fill="#A78BFA"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={22}
                />
                <Bar
                  name={currentTrafficLabel}
                  dataKey="current"
                  fill="#10B981"
                  radius={[4, 4, 0, 0]}
                  maxBarSize={22}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-outline">
              {isLoading
                ? "Đang tải dữ liệu..."
                : "Chưa có giao dịch thanh toán thành công"}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-surface-container-lowest p-4 sm:p-5 rounded-xl border border-surface-variant shadow-(--shadow-level-1)">
          <div className="flex flex-col items-start gap-3 mb-4 sm:flex-row sm:items-center sm:justify-between">
            <h3 className="text-base font-bold text-on-surface">
              Lưu lượng truy cập
            </h3>
            <span className="bg-surface-container text-sm py-1.5 px-3 rounded-lg text-on-surface font-medium">
              {selectedPeriodLabel}
            </span>
          </div>
          <div className="h-64 w-full sm:h-75">
            {trafficData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={trafficData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id="colorCurrent"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorLast" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    strokeDasharray="5 5"
                    vertical={false}
                    stroke="var(--color-surface-variant)"
                  />
                  <XAxis
                    dataKey="name"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: "var(--color-outline)" }}
                    dy={10}
                  />
                  <YAxis
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: "var(--color-outline)" }}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: "8px",
                      border: "none",
                      boxShadow: "var(--shadow-level-2)",
                    }}
                  />
                  <Area
                    name={lastTrafficLabel}
                    type="monotone"
                    dataKey="last"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorLast)"
                  />
                  <Area
                    name={currentTrafficLabel}
                    type="monotone"
                    dataKey="current"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorCurrent)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-outline">
                {isLoading ? "Đang tải dữ liệu..." : "Chưa có dữ liệu truy cập"}
              </div>
            )}
          </div>
        </div>

        <div className="bg-surface-container-lowest p-4 sm:p-5 rounded-xl border border-surface-variant shadow-(--shadow-level-1) flex flex-col">
          <h3 className="text-base font-bold text-on-surface mb-4">Thiết bị</h3>
          <div className="flex-1 h-50 w-full mb-4">
            {deviceData.length > 0 && deviceTotal > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={deviceData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {deviceData.map((entry) => (
                      <Cell
                        key={`cell-${entry.name}`}
                        fill={entry.color}
                        stroke="none"
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      borderRadius: "8px",
                      border: "none",
                      boxShadow: "var(--shadow-level-2)",
                    }}
                    itemStyle={{ color: "var(--color-on-surface)" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-outline">
                {isLoading ? "Đang tải dữ liệu..." : "Chưa có dữ liệu thiết bị"}
              </div>
            )}
          </div>
          <div className="flex justify-between items-center px-4 mt-auto">
            {Object.entries(deviceConfig).map(([key, config]) => {
              const item = deviceData.find((device) => device.name === key);
              const percent =
                deviceTotal > 0
                  ? Math.round(((item?.value ?? 0) / deviceTotal) * 100)
                  : 0;
              const Icon = config.icon;
              return (
                <div key={key} className="flex flex-col items-center">
                  <Icon
                    className="w-5 h-5 mb-1"
                    style={{ color: config.color }}
                  />
                  <span className="text-xs font-medium text-outline">
                    {percent}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-2">
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-variant shadow-(--shadow-level-1) self-start">
          <h3 className="text-base font-bold text-on-surface mb-4">
            Nguồn truy cập
          </h3>
          <div className="w-full" style={{ height: sourceChartHeight }}>
            {showSourceChart ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={sourceData}
                  layout="vertical"
                  margin={{ top: 0, right: 0, left: 20, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    horizontal={false}
                    stroke="var(--color-surface-variant)"
                  />
                  <XAxis
                    allowDecimals={false}
                    type="number"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: "var(--color-outline)" }}
                  />
                  <YAxis
                    dataKey="label"
                    type="category"
                    axisLine={false}
                    tickLine={false}
                    tick={{
                      fontSize: 12,
                      fill: "var(--color-on-surface)",
                      fontWeight: 500,
                    }}
                    width={100}
                  />
                  <Tooltip
                    cursor={{ fill: "var(--color-surface-container-low)" }}
                    contentStyle={{
                      borderRadius: "8px",
                      border: "none",
                      boxShadow: "var(--shadow-level-2)",
                    }}
                  />
                  <Bar
                    dataKey="value"
                    fill="#6366F1"
                    radius={[0, 4, 4, 0]}
                    barSize={20}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-outline">
                {isLoading
                  ? "Đang tải dữ liệu..."
                  : "Chưa có dữ liệu nguồn truy cập"}
              </div>
            )}
          </div>
        </div>

        <div className="bg-surface-container-lowest p-0 rounded-xl border border-surface-variant shadow-(--shadow-level-1) overflow-hidden">
          <div className="p-5 border-b border-surface-variant">
            <h3 className="text-base font-bold text-on-surface">
              Trang phổ biến
            </h3>
          </div>
          <table className="w-full text-left">
            <thead className="bg-surface-container-low/30">
              <tr>
                <th className="py-3 px-5 text-xs font-semibold text-outline uppercase">
                  Trang
                </th>
                <th className="py-3 px-5 text-xs font-semibold text-outline uppercase text-right">
                  Lượt xem
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-variant">
              {overview.popular_pages.length > 0 ? (
                overview.popular_pages.map((page) => (
                  <tr
                    key={page.path}
                    className="hover:bg-surface-container-low/50 transition-colors"
                  >
                    <td className="py-3 px-5 text-sm text-on-surface font-medium truncate max-w-50">
                      <p className="truncate">{page.title || page.path}</p>
                      <p className="text-xs text-outline truncate">
                        {page.path} ·{" "}
                        {page.unique_visitors.toLocaleString("vi-VN")} khách
                      </p>
                    </td>
                    <td className="py-3 px-5 text-sm text-on-surface text-right">
                      {page.views.toLocaleString("vi-VN")}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={2}
                    className="py-10 px-5 text-center text-sm text-outline"
                  >
                    {isLoading
                      ? "Đang tải dữ liệu..."
                      : "Chưa có dữ liệu trang phổ biến"}
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
