import { useEffect } from "react";
import { motion, useSpring, useTransform } from "motion/react";
import {
  Users,
  UserCheck,
  UserPlus,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  MoreHorizontal,
  FileText,
  Award,
  Clock,
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

function Counter({
  value,
  isFloat = false,
  suffix = "",
}: {
  value: number;
  isFloat?: boolean;
  suffix?: string;
}) {
  const spring = useSpring(0, { bounce: 0, duration: 2000 });

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  const display = useTransform(spring, (current) => {
    if (isFloat) {
      return current.toFixed(1) + suffix;
    }
    return Math.round(current).toLocaleString("en-US") + suffix;
  });

  return <motion.span>{display}</motion.span>;
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: "spring", stiffness: 300, damping: 24 },
  },
};

const trafficData = [
  { name: "T1", current: 1240, last: 850 },
  { name: "T2", current: 1530, last: 1300 },
  { name: "T3", current: 1800, last: 1450 },
  { name: "T4", current: 2850, last: 1820 },
  { name: "T5", current: 2600, last: 2010 },
  { name: "T6", current: 3500, last: 2400 },
  { name: "T7", current: 3200, last: 2200 },
  { name: "T8", current: 4100, last: 2850 },
  { name: "T9", current: 3800, last: 2630 },
  { name: "T10", current: 4600, last: 3200 },
  { name: "T11", current: 5200, last: 3500 },
  { name: "T12", current: 4850, last: 3800 },
];

const scoreData = [
  { name: "< 5", users: 12 },
  { name: "5-6", users: 35 },
  { name: "6-7", users: 48 },
  { name: "7-8", users: 85 },
  { name: "8-9", users: 62 },
  { name: "9-10", users: 24 },
];

const recentExams = [
  {
    id: "#EX1254",
    name: "Nguyễn Văn A",
    exam: "Toán giữa kỳ 2",
    score: "9.5",
    status: "Hoàn thành",
    date: "02 thg 5 2026",
    color: "text-[#10B981] bg-[#10B981]/10",
  },
  {
    id: "#EX1253",
    name: "Trần Thị B",
    exam: "Vật lý chương 3",
    score: "7.0",
    status: "Hoàn thành",
    date: "01 thg 5 2026",
    color: "text-[#10B981] bg-[#10B981]/10",
  },
  {
    id: "#EX1252",
    name: "Lê Minh C",
    exam: "Hóa học cơ bản",
    score: "4.5",
    status: "Cần cải thiện",
    date: "30 thg 4 2026",
    color: "text-[#EF4444] bg-[#EF4444]/10",
  },
  {
    id: "#EX1251",
    name: "Phạm Thu D",
    exam: "Sinh học di truyền",
    score: "8.5",
    status: "Hoàn thành",
    date: "29 thg 4 2026",
    color: "text-[#10B981] bg-[#10B981]/10",
  },
  {
    id: "#EX1250",
    name: "Hoàng Văn E",
    exam: "Tiếng Anh Test 1",
    score: "-",
    status: "Đang làm",
    date: "28 thg 4 2026",
    color: "text-[#F59E0B] bg-[#F59E0B]/10",
  },
];

export function Dashboard() {
  return (
    <div className="p-4 md:p-6 space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-on-surface">
            CRM Overview
          </h1>
        </div>
      </div>

      {/* Metrics */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5"
      >
        {[
          {
            label: "Tổng đề thi",
            icon: UserCheck,
            value: 12450,
            isFloat: false,
            suffix: "",
            trend: "+12.5%",
            isUp: true,
            subtext: "so với tháng trước",
          },
          {
            label: "User mới",
            value: 350,
            isFloat: false,
            suffix: "",
            trend: "+5.1%",
            isUp: true,
            subtext: "so với tháng trước",
          },
          {
            label: "Đang hoạt động",

            value: 1233,
            isFloat: false,
            suffix: "",
            trend: "+0.2",
            isUp: true,
            subtext: "so với tháng trước",
          },
          {
            label: "Kỳ thi đang mở",
            icon: Clock,
            value: 15,
            isFloat: false,
            suffix: "",
            trend: "-2",
            isUp: false,
            subtext: "so với tuần trước",
          },
        ].map((stat, i) => (
          <motion.div
            key={i}
            variants={itemVariants}
            className="bg-surface-container-lowest rounded-xl p-5 border border-surface-variant shadow-[var(--shadow-level-1)] flex flex-col justify-between"
          >
            <div>
              <p className="text-kpi-title font-medium text-base">
                {stat.label}
              </p>
              <h3 className="text-2xl font-bold text-on-surface mt-1">
                <Counter
                  value={stat.value}
                  isFloat={stat.isFloat}
                  suffix={stat.suffix}
                />
              </h3>
            </div>
            <div className="flex items-center gap-2 mt-4">
              <div
                className={`flex items-center text-sm font-semibold tracking-wide ${stat.isUp ? "text-[#10B981]" : "text-[#EF4444]"}`}
              >
                {stat.trend}
              </div>
              <span className="text-xs text-on-surface-variant font-medium">
                {stat.subtext}
              </span>
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Main Area Chart */}
        <div className="xl:col-span-2 bg-surface-container-lowest rounded-xl p-6 border border-surface-variant shadow-[var(--shadow-level-1)]">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-lg font-bold text-on-surface">
                Lưu lượng làm bài
              </h2>
              <p className="text-sm text-on-surface-variant mt-1">
                Lượt truy cập hệ thống thi
              </p>
            </div>
            <select className="bg-surface-container text-sm py-1.5 px-3 rounded-lg text-on-surface outline-none">
              <option>Năm nay</option>
              <option>Năm ngoái</option>
            </select>
          </div>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={trafficData}
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
                  tickFormatter={(val) => `${val}`}
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
                  name="Năm ngoái"
                  stroke="var(--color-outline)"
                  fillOpacity={1}
                  fill="url(#colorLast)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="current"
                  name="Năm nay"
                  stroke="var(--color-primary)"
                  fillOpacity={1}
                  fill="url(#colorCurrent)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Small Bar Chart / Activity */}
        <div className="xl:col-span-1 bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-on-surface">Phổ điểm tuần</h3>
            <button className="text-outline hover:text-on-surface">
              <MoreHorizontal className="w-5 h-5" />
            </button>
          </div>
          <div className="h-[200px] w-full mb-6 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={scoreData}
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
            <div className="flex items-center justify-between py-3 border-t border-surface-variant">
              <div>
                <p className="text-sm font-semibold text-on-surface">
                  Phổ điểm nhiều nhất
                </p>
                <p className="text-xs text-outline">
                  7 đến 8 điểm (85 học sinh)
                </p>
              </div>
              <div className="px-2.5 py-1 bg-primary-fixed text-on-primary-fixed text-xs font-semibold rounded-md">
                32%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Exams Table */}
      <div className="bg-surface-container-lowest rounded-xl shadow-[var(--shadow-level-1)] overflow-hidden">
        <div className="p-6 border-b border-surface-variant flex justify-between items-center">
          <h3 className="text-lg font-bold text-on-surface">
            Kết quả thi mới nhất
          </h3>
          <button className="text-primary text-sm font-semibold hover:underline">
            Xem tất cả
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low/30 border-b border-surface-variant">
                <th className="py-4 px-6 text-[12px] font-semibold text-outline uppercase tracking-wider">
                  Mã Bài Thi
                </th>
                <th className="py-4 px-6 text-[12px] font-semibold text-outline uppercase tracking-wider">
                  Học sinh
                </th>
                <th className="py-4 px-6 text-[12px] font-semibold text-outline uppercase tracking-wider">
                  Kỳ thi
                </th>
                <th className="py-4 px-6 text-[12px] font-semibold text-outline uppercase tracking-wider">
                  Ngày nộp
                </th>
                <th className="py-4 px-6 text-[12px] font-semibold text-outline uppercase tracking-wider">
                  Điểm số
                </th>
                <th className="py-4 px-6 text-[12px] font-semibold text-outline uppercase tracking-wider">
                  Đánh giá
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-variant">
              {recentExams.map((exam, i) => (
                <tr
                  key={i}
                  className="hover:bg-surface-container-low/30 transition-colors"
                >
                  <td className="py-4 px-6 text-sm font-medium text-primary">
                    {exam.id}
                  </td>
                  <td className="py-4 px-6 text-sm font-semibold text-on-surface">
                    {exam.name}
                  </td>
                  <td className="py-4 px-6 text-sm text-outline">
                    {exam.exam}
                  </td>
                  <td className="py-4 px-6 text-sm text-outline">
                    {exam.date}
                  </td>
                  <td className="py-4 px-6 text-sm font-medium text-on-surface">
                    {exam.score}
                  </td>
                  <td className="py-4 px-6">
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded text-xs font-semibold ${exam.color}`}
                    >
                      {exam.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
