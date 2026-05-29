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
  ArrowDownRight,
  ArrowUpRight,
  Monitor,
  Smartphone,
  Tablet,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

export function Analytics() {
  const kpiData = [
    {
      title: "Lưu lượng Truy cập",
      value: "32.8K",
      unit: "Lượt",
      change: "+18.45%",
      isPositive: true,
      linkText: "Khám phá Lượng truy cập",
    },
    {
      title: "Lượt xem Trang",
      value: "102.4K",
      unit: "Lượt",
      change: "+8.20%",
      isPositive: true,
      linkText: "Khám phá Lượt xem",
    },
    {
      title: "Tỷ lệ Thoát",
      value: "42.3",
      unit: "%",
      change: "-2.40%",
      isPositive: true,
      linkText: "Khám phá Tỷ lệ thoát",
    },
    {
      title: "Người dùng Đang truy cập",
      value: "312",
      unit: "Người",
      change: "+12.10%",
      isPositive: true,
      linkText: "Khám phá Người dùng",
    },
  ];

  const trafficData = [
    { name: "T2", users: 4000, views: 2400 },
    { name: "T3", users: 3000, views: 1398 },
    { name: "T4", users: 2000, views: 9800 },
    { name: "T5", users: 2780, views: 3908 },
    { name: "T6", users: 1890, views: 4800 },
    { name: "T7", users: 2390, views: 3800 },
    { name: "CN", users: 3490, views: 4300 },
  ];

  const deviceData = [
    { name: "Desktop", value: 55, color: "#4F46E5" }, // Indigo 600
    { name: "Mobile", value: 35, color: "#10B981" }, // Emerald 500
    { name: "Tablet", value: 10, color: "#F59E0B" }, // Amber 500
  ];

  const sourceData = [
    { name: "Tìm kiếm tự nhiên", value: 45 },
    { name: "Mạng xã hội", value: 25 },
    { name: "Trực tiếp", value: 20 },
    { name: "Khác", value: 10 },
  ];

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">
            Analysis
          </h1>
        </div>
        <div className="flex gap-2">
          <select className="bg-surface-container-lowest border border-surface-variant text-sm py-2 px-4 rounded-lg focus:outline-none focus:border-primary cursor-pointer text-on-surface">
            <option>7 ngày qua</option>
            <option>30 ngày qua</option>
            <option>Năm nay</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {kpiData.map((kpi, i) => (
          <div
            key={i}
            className="bg-surface-container-lowest rounded-xl border border-surface-variant shadow-(--shadow-level-1) flex flex-col"
          >
            <div className="flex justify-between items-start p-4 border-b border-dashed border-outline-variant">
              <p className="text-kpi-title text-base leading-tight whitespace-pre-line font-medium">
                {kpi.title}
              </p>
              <span
                className={`text-sm font-semibold tracking-wide ${kpi.isPositive ? "text-emerald-500" : "text-red-500"}`}
              >
                {kpi.change}
              </span>
            </div>
            <div className="p-4 flex flex-col flex-1">
              <h3 className="text-xl leading-none mb-4 text-on-surface flex items-baseline gap-1.5">
                <span className="font-semibold">{kpi.value}</span>
                <span className="text-sm font-normal">{kpi.unit}</span>
              </h3>
              <div className="flex items-center justify-between mt-auto">
                <div className="w-10 h-10 rounded-lg border border-surface-variant p-1 shadow-sm shrink-0">
                  <div
                    className={`w-full h-full rounded flex items-center justify-center text-white ${kpi.isPositive ? "bg-emerald-500" : "bg-red-500"}`}
                  >
                    {kpi.isPositive ? (
                      <TrendingUp className="w-4 h-4" strokeWidth={2.5} />
                    ) : (
                      <TrendingDown className="w-4 h-4" strokeWidth={2.5} />
                    )}
                  </div>
                </div>
                <a
                  href="#"
                  className="text-sm font-medium text-kpi-link border-b border-kpi-link hover:opacity-80 transition-opacity pb-0.5 whitespace-nowrap overflow-hidden text-ellipsis ml-2"
                >
                  {kpi.linkText}
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        <div className="lg:col-span-2 bg-surface-container-lowest p-5 rounded-xl border border-surface-variant shadow-(--shadow-level-1)">
          <h3 className="text-base font-bold text-on-surface mb-6">
            Lưu lượng truy cập
          </h3>
          <div className="h-75 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={trafficData}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorUsers" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorViews" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
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
                  name="views"
                  type="monotone"
                  dataKey="views"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorViews)"
                />
                <Area
                  name="users"
                  type="monotone"
                  dataKey="users"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorUsers)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-variant shadow-(--shadow-level-1) flex flex-col">
          <h3 className="text-base font-bold text-on-surface mb-6">Thiết bị</h3>
          <div className="flex-1 h-50 w-full mb-4">
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
                  {deviceData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
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
          </div>
          <div className="flex justify-between items-center px-4 mt-auto">
            <div className="flex flex-col items-center">
              <Monitor className="w-5 h-5 text-indigo-600 mb-1" />
              <span className="text-xs font-medium text-outline">55%</span>
            </div>
            <div className="flex flex-col items-center">
              <Smartphone className="w-5 h-5 text-emerald-500 mb-1" />
              <span className="text-xs font-medium text-outline">35%</span>
            </div>
            <div className="flex flex-col items-center">
              <Tablet className="w-5 h-5 text-amber-500 mb-1" />
              <span className="text-xs font-medium text-outline">10%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 mt-2">
        <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-variant shadow-(--shadow-level-1)">
          <h3 className="text-base font-bold text-on-surface mb-6">
            Nguồn truy cập
          </h3>
          <div className="h-62.5 w-full">
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
                  type="number"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: "var(--color-outline)" }}
                />
                <YAxis
                  dataKey="name"
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
              <tr className="hover:bg-surface-container-low/50 transition-colors">
                <td className="py-3 px-5 text-sm text-on-surface font-medium truncate max-w-50">
                  /dashboard
                </td>
                <td className="py-3 px-5 text-sm text-on-surface text-right">
                  12,430
                </td>
              </tr>
              <tr className="hover:bg-surface-container-low/50 transition-colors">
                <td className="py-3 px-5 text-sm text-on-surface font-medium truncate max-w-50">
                  /courses/advanced-calculus
                </td>
                <td className="py-3 px-5 text-sm text-on-surface text-right">
                  8,210
                </td>
              </tr>
              <tr className="hover:bg-surface-container-low/50 transition-colors">
                <td className="py-3 px-5 text-sm text-on-surface font-medium truncate max-w-50">
                  /students/directory
                </td>
                <td className="py-3 px-5 text-sm text-on-surface text-right">
                  6,541
                </td>
              </tr>
              <tr className="hover:bg-surface-container-low/50 transition-colors">
                <td className="py-3 px-5 text-sm text-on-surface font-medium truncate max-w-50">
                  /exams/schedule
                </td>
                <td className="py-3 px-5 text-sm text-on-surface text-right">
                  4,320
                </td>
              </tr>
              <tr className="hover:bg-surface-container-low/50 transition-colors">
                <td className="py-3 px-5 text-sm text-on-surface font-medium truncate max-w-50">
                  /profile/settings
                </td>
                <td className="py-3 px-5 text-sm text-on-surface text-right">
                  2,110
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
