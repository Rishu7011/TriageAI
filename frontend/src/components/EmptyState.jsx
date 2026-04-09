import { Activity, Target, Zap, Clock, AlertTriangle } from 'lucide-react';

const EmptyState = ({ onLoadDemo }) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] px-4 w-full">
      <div className="flex flex-col items-center max-w-3xl text-center mb-12 animate-slide-in-top">
        <div className="w-16 h-16 bg-[#e11d48] rounded-2xl flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(225,29,72,0.4)]">
          <Activity className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-4xl font-bold text-white mb-4 tracking-tight">TriageAI</h1>
        <p className="text-gray-400 text-lg max-w-2xl leading-relaxed">
          AI-powered Emergency Department triage: continuously re-scoring every patient using vitals, time-in-ED, age, comorbidities, and a trained GBM model.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl w-full mb-12">
        <div className="bg-[#1e2336] border border-white/5 p-6 rounded-xl flex flex-col gap-3 hover:bg-[#252b42] transition-colors">
          <div className="flex items-center gap-2 text-white font-medium">
            <Target className="w-5 h-5 text-red-500" /> Live Risk Scoring
          </div>
          <p className="text-sm text-gray-400 leading-relaxed">
            Multiplicative composite formula: base_risk × time_decay × age_modifier × comorbidity × ML score
          </p>
        </div>

        <div className="bg-[#1e2336] border border-white/5 p-6 rounded-xl flex flex-col gap-3 hover:bg-[#252b42] transition-colors">
          <div className="flex items-center gap-2 text-white font-medium">
            <Zap className="w-5 h-5 text-blue-400" /> SHAP Explanations
          </div>
          <p className="text-sm text-gray-400 leading-relaxed">
            GradientBoostingClassifier + SHAP TreeExplainer — every risk score explained, not just a number
          </p>
        </div>

        <div className="bg-[#1e2336] border border-white/5 p-6 rounded-xl flex flex-col gap-3 hover:bg-[#252b42] transition-colors">
          <div className="flex items-center gap-2 text-white font-medium">
            <Clock className="w-5 h-5 text-orange-400" /> Time-Lapse Simulation
          </div>
          <p className="text-sm text-gray-400 leading-relaxed">
            Simulate 90 minutes of ED evolution and watch patient trajectories escalate or stabilize
          </p>
        </div>

        <div className="bg-[#1e2336] border border-white/5 p-6 rounded-xl flex flex-col gap-3 hover:bg-[#252b42] transition-colors">
          <div className="flex items-center gap-2 text-white font-medium">
            <AlertTriangle className="w-5 h-5 text-yellow-500" /> Intelligent Alerting
          </div>
          <p className="text-sm text-gray-400 leading-relaxed">
            Threshold-based alerts fire when risk ≥ 7.5 — identifying critical deterioration before a patient crashes
          </p>
        </div>
      </div>

      <div className="flex flex-col items-center">
        <button 
          onClick={onLoadDemo}
          className="px-8 py-3.5 bg-[#e11d48] hover:bg-[#be123c] text-white rounded-lg font-medium transition-all shadow-[0_0_20px_rgba(225,29,72,0.4)] hover:shadow-[0_0_30px_rgba(225,29,72,0.6)] transform hover:-translate-y-0.5 flex items-center gap-2"
        >
          <Activity className="w-5 h-5" />
          Load 10-Patient Demo
        </button>
        <p className="text-xs text-gray-500 mt-6">
          Includes demo patients covering ESI 1-5 triage levels
        </p>
      </div>
    </div>
  );
};

export default EmptyState;
