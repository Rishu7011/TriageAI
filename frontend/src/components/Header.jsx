import { Activity, Bell, Settings, FastForward, RotateCcw } from 'lucide-react';
import { useEffect, useState } from 'react';

const Header = ({ onSimulate, queueLength = 0, alertsCount = 0, lastUpdated, onRescore, currentPage, setCurrentPage }) => {
  const [secondsAgo, setSecondsAgo] = useState(0);

  useEffect(() => {
    if (!lastUpdated) return;
    setSecondsAgo(0);
    const interval = setInterval(() => {
      setSecondsAgo(Math.floor((Date.now() - lastUpdated) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [lastUpdated]);

  return (
    <header className="flex items-center justify-between py-4 mb-6 border-b border-white/5 bg-[#0b0f19] shrink-0 sticky top-0 z-50">
      
      {/* Left portion: Logo and Stats */}
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[#e11d48] rounded flex items-center justify-center">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-green-400 tracking-tight leading-tight">
              TriageAI
            </h1>
            <p className="text-[10px] text-gray-500 uppercase tracking-widest font-mono">
              Continuous Triage<br/>Intelligence System
            </p>
          </div>
        </div>

        {/* Stats Blocks */}
        <div className="hidden lg:flex items-center gap-3">
          <div className="bg-[#151923] border border-white/5 px-4 py-2 rounded flex flex-col justify-center min-w-[100px] shrink-0">
             <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-1 whitespace-nowrap">Patients Active</span>
             <span className="text-white font-bold text-lg leading-none">{queueLength}</span>
          </div>
          <div className="bg-[#151923] border border-white/5 px-4 py-2 rounded flex flex-col justify-center min-w-[100px] shrink-0">
             <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider mb-1 whitespace-nowrap">Critical</span>
             <span className="text-red-500 font-bold text-lg leading-none">{alertsCount}</span>
          </div>
          <div className="bg-[#151923] border border-white/5 px-4 py-2 rounded flex flex-col justify-center min-w-[130px] shrink-0 relative group">
             <div className="flex items-center justify-between mb-1 gap-2">
               <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider whitespace-nowrap">Last Rescore</span>
               <button 
                 onClick={onRescore} 
                 className="flex items-center gap-1 text-[9px] text-[#10b981] hover:text-white uppercase tracking-wider font-bold transition-colors"
                 title="Force Rescore"
               >
                 <RotateCcw className="w-2.5 h-2.5" /> Force
               </button>
             </div>
             <span className="text-green-400 font-bold text-sm leading-none flex items-center gap-2">
                {secondsAgo}s ago <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
             </span>
          </div>
        </div>
      </div>

      {/* Center portion: Navigation */}
      <nav className="hidden xl:flex items-center gap-6 text-sm font-medium text-gray-400 shrink-0">
        <div 
          onClick={() => setCurrentPage?.('dashboard')}
          className={`cursor-pointer transition-colors pb-1 border-b-2 whitespace-nowrap ${currentPage === 'dashboard' ? 'text-green-400 border-green-400' : 'hover:text-white border-transparent'}`}
        >
          Dashboard
        </div>
        <div 
          onClick={() => setCurrentPage?.('whatif')}
          className={`cursor-pointer transition-colors pb-1 border-b-2 whitespace-nowrap ${currentPage === 'whatif' ? 'text-green-400 border-green-400' : 'hover:text-white border-transparent'}`}
        >
          What-If
        </div>
        <div 
          onClick={() => setCurrentPage?.('timelapse')}
          className={`cursor-pointer transition-colors pb-1 border-b-2 whitespace-nowrap ${currentPage === 'timelapse' ? 'text-green-400 border-green-400' : 'hover:text-white border-transparent'}`}
        >
          Time-Lapse
        </div>
      </nav>
      
      {/* Right portion: Actions */}
      <div className="flex items-center gap-4 shrink-0">
        <button 
          onClick={() => onSimulate('demo')}
          className="px-5 py-2 text-sm bg-transparent border border-white/10 hover:border-white/30 text-white rounded font-medium transition-colors whitespace-nowrap"
        >
          Load Demo Patients
        </button>
        <button 
          onClick={() => onSimulate(90)}
          className="px-5 py-2 text-sm bg-[#e11d48] hover:bg-[#be123c] text-white rounded font-medium transition-colors shadow-lg flex items-center gap-2"
        >
          <FastForward className="w-4 h-4 text-yellow-300 fill-yellow-300" />
          Simulate 90 min
        </button>
        
        <div className="w-px h-6 bg-white/10 mx-2"></div>
        
        <button className="text-gray-400 hover:text-white transition-colors">
          <Bell className="w-5 h-5" />
        </button>
        <button className="text-gray-400 hover:text-white transition-colors">
          <Settings className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
};

export default Header;
