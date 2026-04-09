import { Asterisk, AlertTriangle } from 'lucide-react';
import { forwardRef } from 'react';
import clsx from 'clsx';

const PatientCard = forwardRef(({ patient, onClick, isActive }, ref) => {
  const riskScore = (patient.risk_probability || 0) * 10;
  const isHighRisk = riskScore > 7.5;
  const isMediumRisk = riskScore > 4.5 && riskScore <= 7.5;

  let borderColor = 'border-white/5';
  let bgColor = 'bg-[#151923] hover:bg-[#1a1f2e]';
  let dotColor = 'bg-green-500';
  
  if (isActive) {
    borderColor = isHighRisk ? 'border-red-500/50 shadow-[0_0_20px_rgba(239,68,68,0.2)]' : 'border-gray-400 shadow-[0_0_20px_rgba(255,255,255,0.1)]';
    bgColor = 'bg-[#1e2436]';
  } else if (isHighRisk) {
    borderColor = 'border-red-500/30';
  }

  if (isHighRisk) dotColor = 'bg-red-500';
  else if (isMediumRisk) dotColor = 'bg-yellow-500';

  const formatAgeSex = `${patient.age || '--'}Y • ${patient.sex ? patient.sex.charAt(0) : 'U'}`;

  return (
    <div 
      ref={ref}
      onClick={() => onClick(patient)}
      className={clsx(
        "relative rounded-xl p-4 cursor-pointer transition-all duration-300 border",
        bgColor, borderColor
      )}
    >
      {/* Top Section */}
      <div className="flex gap-4 items-start">
        {/* Risk Icon Block */}
        <div className={clsx(
          "w-12 h-12 rounded-lg flex items-center justify-center shrink-0",
          isHighRisk ? "bg-red-500/10 text-red-400" : "bg-white/5 text-gray-400"
        )}>
           {isHighRisk ? <Asterisk className="w-6 h-6" /> : <div className="w-4 h-4 rounded-full bg-current opacity-50" />}
        </div>

        {/* Info Block */}
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start mb-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-bold text-white text-lg truncate">{patient.name || `Patient #${String(patient.patient_id).slice(0, 4)}`}</h3>
              <span className="text-xs font-semibold text-gray-400 tracking-wider">
                {formatAgeSex}
              </span>
              <span className={clsx(
                "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider",
                patient.acuity_changed ? "bg-red-500 text-white" : "bg-white/10 text-gray-300"
              )}>
                ESI-{patient.esi_level || 3} {patient.acuity_changed && "(ESCALATED)"}
              </span>
            </div>

            {/* Risk Score */}
            <div className="flex flex-col items-end shrink-0 pl-4">
              <span className="text-[10px] text-gray-500 font-bold tracking-widest uppercase mb-0.5">Risk Score</span>
              <div className="flex items-center gap-2">
                <span className={clsx("w-2 h-2 rounded-full", dotColor, isHighRisk && "animate-pulse")} />
                <span className="text-3xl font-bold text-white leading-none">{riskScore.toFixed(1)}</span>
              </div>
            </div>
          </div>

          {/* Chief Complaint */}
          <div className="flex items-start gap-1.5 mb-4 pr-16 text-sm text-gray-300 leading-snug">
            {isHighRisk && <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />}
            <p className="line-clamp-2">{patient.chief_complaint || patient.symptom_category}</p>
          </div>

          {/* Vitals Pills */}
          <div className="flex flex-wrap gap-2">
            <div className={clsx("px-2.5 py-1 rounded bg-[#252b42] flex flex-col justify-center", patient.hr > 100 && "bg-red-500/20 text-red-300")}>
              <span className="text-[9px] uppercase tracking-wider font-bold text-gray-500">HR</span>
              <span className="text-xs font-bold text-white">{patient.hr || '--'} <span className="font-normal opacity-60">bpm</span></span>
            </div>
            
            <div className={clsx("px-2.5 py-1 rounded bg-[#252b42] flex flex-col justify-center", (patient.sbp > 140 || patient.sbp < 90) && "bg-red-500/20 text-red-300")}>
              <span className="text-[9px] uppercase tracking-wider font-bold text-gray-500">BP</span>
              <span className="text-xs font-bold text-white">{patient.sbp || '--'}/{patient.dbp || '--'}</span>
            </div>

            <div className={clsx("px-2.5 py-1 rounded bg-[#252b42] flex flex-col justify-center", patient.spo2 < 93 && "bg-yellow-500/20 text-yellow-300")}>
              <span className="text-[9px] uppercase tracking-wider font-bold text-gray-500">SpO2</span>
              <span className="text-xs font-bold text-white">{patient.spo2 || '--'}%</span>
            </div>

            <div className="px-2.5 py-1 rounded bg-white/5 flex flex-col justify-center border border-white/5">
              <span className="text-[9px] uppercase tracking-wider font-bold text-gray-500">Wait</span>
              <span className="text-xs font-bold flex gap-1">
                <span className="text-gray-300">{patient.wait_time_min || 0}</span>
                <span className="text-gray-500">min</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

PatientCard.displayName = 'PatientCard';
export default PatientCard;
