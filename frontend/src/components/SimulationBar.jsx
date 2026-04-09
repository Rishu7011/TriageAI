import { Download } from 'lucide-react';

const SimulationBar = ({ onSimulate }) => {
  return (
    <div className="absolute bottom-0 w-full left-0 bg-[#0b0f19] border-t border-white/5 py-4 px-6 flex items-center justify-between z-50">
      
      {/* Simulation Controls */}
      <div className="flex items-center gap-6">
        <span className="text-[10px] text-gray-500 font-bold tracking-widest uppercase">Simulation Mode</span>
        <div className="flex gap-2">
          <button className="px-5 py-2 bg-[#10b981] hover:bg-[#059669] text-white text-xs font-bold rounded tracking-wider shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-colors">
            REAL-TIME
          </button>
          <button 
            onClick={() => onSimulate(30)}
            className="px-5 py-2 bg-[#1e2336] hover:bg-white/10 text-gray-400 hover:text-white text-xs font-bold rounded tracking-wider border border-white/5 transition-colors"
          >
            +30M
          </button>
          <button 
            onClick={() => onSimulate(60)}
            className="px-5 py-2 bg-[#1e2336] hover:bg-white/10 text-gray-400 hover:text-white text-xs font-bold rounded tracking-wider border border-white/5 transition-colors"
          >
            +60M
          </button>
          <button 
            onClick={() => onSimulate(90)}
            className="px-5 py-2 bg-[#1e2336] hover:bg-white/10 text-gray-400 hover:text-white text-xs font-bold rounded tracking-wider border border-white/5 transition-colors"
          >
            +90M
          </button>
        </div>
      </div>

      {/* Predictive Insights */}
      <div className="hidden lg:flex flex-col items-center">
        <span className="text-[9px] text-gray-500 font-bold tracking-widest uppercase mb-1">Predictive Insights</span>
        <span className="text-[#10b981] text-xs font-bold tracking-wider uppercase">4 Patients at risk in +90min</span>
      </div>

      {/* Export & Disclaimer */}
      <div className="flex items-center gap-8">
        <button className="flex items-center gap-2 text-xs font-bold text-gray-400 hover:text-white tracking-wider uppercase transition-colors">
          <Download className="w-4 h-4" /> Export Audit Log
        </button>
        <p className="text-[8px] text-gray-600 font-mono text-right max-w-[300px] leading-relaxed hidden xl:block">
          MEDICAL DISCLAIMER: TRIAGEAI DECISION-SUPPORT TOOL. SCORES MUST BE CLINICALLY VALIDATED BY AUTHORIZED PERSONNEL.
        </p>
      </div>

    </div>
  );
};

export default SimulationBar;
