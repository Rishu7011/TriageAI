import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass p-3 rounded-lg border border-white/10 shadow-2xl">
        <p className="text-gray-300 text-sm mb-1">{payload[0].payload.feature}</p>
        <p className="text-white font-bold">
          Contribution: <span className="text-red-400">+{payload[0].value.toFixed(2)}</span>
        </p>
      </div>
    );
  }
  return null;
};

const ShapChart = ({ labels, values }) => {
  if (!labels || !values || labels.length === 0 || values.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500 glass rounded-xl border border-white/5">
        No explainability data available
      </div>
    );
  }

  // Format data for Recharts by zipping labels and values
  const chartData = labels.map((label, i) => ({
    feature: label,
    value: values[i]
  })).sort((a, b) => b.value - a.value).slice(0, 8);

  return (
    <div className="h-full min-h-[400px] w-full p-6 bg-[#151923] rounded-xl border border-white/5 relative flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xs font-bold text-gray-500 tracking-widest uppercase flex items-center gap-2">
          AI Risk Explainer (SHAP)
        </h3>
        <div className="w-4 h-4 rounded-full border border-gray-500 text-gray-500 flex items-center justify-center text-[10px] cursor-help">?</div>
      </div>

      <div className="flex-1 flex flex-col gap-3 justify-center">
        {chartData.map((item, idx) => (
           <div key={idx} className="relative w-full">
             <div className="flex justify-between items-end mb-2">
                <span className="text-[10px] font-bold text-gray-400 tracking-wider uppercase">{item.feature}</span>
                <span className="text-xs font-bold text-white">{(item.value > 0 ? '+' : '')}{item.value.toFixed(1)}</span>
             </div>
             <div className="h-1.5 w-full bg-[#1e2336] rounded-full overflow-hidden">
                <div 
                  className={`h-full rounded-full transition-all duration-1000 ${item.value > 0 ? 'bg-red-500' : 'bg-blue-500'}`}
                  style={{ width: `${Math.min(Math.abs(item.value) * 30, 100)}%` }}
                ></div>
             </div>
           </div>
        ))}
      </div>

      <div className="mt-8 pt-8 border-t border-white/5 relative flex flex-col items-center justify-center">
         {/* Diamond visual BG */}
         <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 border border-red-500/10 rotate-45 pointer-events-none"></div>
         <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 border border-red-500/10 rotate-45 pointer-events-none"></div>
         
         <span className="text-[10px] font-bold text-gray-500 tracking-widest uppercase mb-2">Final Adjusted Score</span>
         <span className="text-5xl font-bold text-red-500 drop-shadow-[0_0_20px_rgba(239,68,68,0.4)]">
           {(chartData.reduce((acc, curr) => acc + curr.value, 0) + 4.0).toFixed(1)}
         </span>
      </div>
    </div>
  );
};

export default ShapChart;
