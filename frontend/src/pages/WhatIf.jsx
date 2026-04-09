import { useState, useEffect } from 'react';
import { Zap, Loader2 } from 'lucide-react';
import Header from '../components/Header';
import api from '../services/api';

const WhatIf = ({ setCurrentPage }) => {
  const [horizon, setHorizon] = useState(60);
  const [loading, setLoading] = useState(false);
  const [currentQueue, setCurrentQueue] = useState([]);
  const [predictedQueue, setPredictedQueue] = useState([]);

  useEffect(() => {
    const fetchCurrent = async () => {
      try {
        const res = await api.get('/api/queue?no_rescore=true');
        // Sort descending by risk score
        const sorted = res.data.sort((a, b) => b.risk_probability - a.risk_probability);
        setCurrentQueue(sorted);
      } catch (err) {
        console.error('Failed to fetch current queue:', err);
      }
    };
    fetchCurrent();
  }, []);

  const runPrediction = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/patients/whatif?future_minutes=${horizon}`);
      setPredictedQueue(res.data);
    } catch (err) {
      console.error('Prediction failed:', err);
    } finally {
      setLoading(false);
    }
  };

  // Map predicted queue by patient_id for fast lookup
  const predictedMap = predictedQueue.reduce((acc, p) => {
    acc[p.patient_id] = p;
    return acc;
  }, {});

  const horizons = [30, 60, 90, 120];

  return (
    <div className="max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 flex flex-col h-screen overflow-hidden">
      <Header 
        currentPage="whatif"
        setCurrentPage={setCurrentPage} 
        onSimulate={() => {}} 
        queueLength={currentQueue.length} 
        alertsCount={currentQueue.filter(p => (p.risk_probability * 10) > 7.5).length}
        lastUpdated={Date.now()}
      />

      <div className="flex-1 overflow-y-auto pb-20 mt-4 pr-2">
        
        {/* Controls Section */}
        <div className="mb-8 border-b border-white/5 pb-8">
          <p className="text-gray-400 mb-6 max-w-4xl font-mono text-sm leading-relaxed">
            Choose a future time horizon and see how the queue risk distribution shifts. Key demo point: watch ESI-3 patients escalate based on ML predictions.
          </p>

          <div className="flex items-center gap-4">
            <span className="text-gray-500 font-mono text-sm tracking-widest">Simulate +</span>
            
            <div className="flex gap-2">
              {horizons.map(m => (
                <button
                  key={m}
                  onClick={() => setHorizon(m)}
                  className={`px-4 py-2 font-mono text-sm rounded transition-colors ${
                    horizon === m 
                      ? 'bg-[#e11d48] text-white' 
                      : 'bg-[#151923] text-gray-400 hover:text-white border border-white/5'
                  }`}
                >
                  {m}m
                </button>
              ))}
            </div>

            <button 
              onClick={runPrediction}
              disabled={loading}
              className="px-6 py-2 ml-4 font-bold text-sm bg-[#e11d48] hover:bg-[#be123c] text-white rounded transition-colors flex items-center gap-2 shadow-lg disabled:opacity-50"
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Running...</>
              ) : (
                <><Zap className="w-4 h-4" /> Run What-If</>
              )}
            </button>
          </div>
        </div>

        {/* Column Headers */}
        <div className="grid grid-cols-2 gap-8 mb-4">
          <div className="text-center font-mono text-[10px] uppercase tracking-widest text-gray-500">NOW</div>
          <div className="text-center font-mono text-[10px] uppercase tracking-widest text-gray-500">+{horizon}min (predicted)</div>
        </div>

        {/* Comparisons */}
        <div className="flex flex-col gap-4">
          {currentQueue.map((patient) => {
            const currentRisk = patient.risk_probability * 10;
            const pred = predictedMap[patient.patient_id];
            let predictedRisk = currentRisk;
            let predAlert = patient.alert_level;
            
            if (pred) {
              predictedRisk = pred.risk_probability * 10;
              predAlert = pred.alert_level;
            }
            
            const delta = predictedRisk - currentRisk;
            const hasEscalated = delta > 0.5; // Threshold for displaying red change
            const becameCritical = predAlert === 'CRITICAL' && patient.alert_level !== 'CRITICAL';

            return (
              <div key={patient.patient_id} className="grid grid-cols-2 gap-8 items-stretch">
                
                {/* NOW Card */}
                <div className="bg-[#151923] border border-white/5 rounded-xl p-5 flex flex-col justify-center">
                  <h3 className="font-bold text-gray-200 mb-2">{patient.name}</h3>
                  <div className="flex gap-2 items-center">
                    <span className="font-mono text-lg font-bold text-red-500">{currentRisk.toFixed(1)}<span className="text-gray-600 text-sm">/10</span></span>
                    <span className="text-[10px] uppercase tracking-wider text-gray-400">{patient.alert_level}</span>
                  </div>
                </div>

                {/* PREDICTED Card */}
                {pred ? (
                  <div className={`border rounded-xl p-5 flex flex-col justify-center transition-all ${
                    becameCritical || hasEscalated 
                      ? 'bg-red-950/20 border-red-500/30 shadow-[0_0_15px_rgba(220,38,38,0.1)]' 
                      : 'bg-[#151923] border-white/5'
                  }`}>
                    <div className="flex gap-2 items-center mb-1">
                      <span className="font-mono text-lg font-bold text-gray-200">
                        {delta > 0.1 ? '▲' : delta < -0.1 ? '▼' : '-'} {predictedRisk.toFixed(1)}<span className="text-gray-600 text-sm">/10</span>
                      </span>
                      {becameCritical && (
                        <span className="text-[10px] uppercase tracking-wider text-red-400 font-bold ml-2">→ CRITICAL</span>
                      )}
                    </div>
                    <div className="font-mono text-[10px] text-gray-500">
                      <span className={delta > 0.1 ? 'text-red-400 font-bold' : ''}>
                        {delta > 0 ? '+' : ''}{delta.toFixed(1)} pts
                      </span> in {horizon}min
                    </div>
                  </div>
                ) : (
                  <div className="bg-[#151923]/50 border border-transparent border-dashed rounded-xl p-5 flex items-center justify-center text-gray-600 font-mono text-sm">
                    {loading ? 'Calculating...' : 'Click Run to generate prediction'}
                  </div>
                )}

              </div>
            );
          })}

          {currentQueue.length === 0 && (
            <div className="col-span-2 text-center py-20 text-gray-500 font-mono">
              No patients in queue. Return to dashboard to load demo data.
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

export default WhatIf;
