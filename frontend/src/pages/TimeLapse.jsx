import { useState, useEffect } from 'react';
import { Loader2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import Header from '../components/Header';
import api from '../services/api';

const COLORS = [
  '#ef4444', '#f59e0b', '#eab308', '#22c55e', '#3b82f6', 
  '#a855f7', '#ec4899', '#14b8a6', '#f97316', '#6366f1'
];

const TimeLapse = ({ setCurrentPage }) => {
  const [horizon, setHorizon] = useState(120);
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState([]);
  const [patientNames, setPatientNames] = useState([]);
  const [activeQueueCount, setActiveQueueCount] = useState(0);
  const [alertsCount, setAlertsCount] = useState(0);

  // Fetch current queue metadata for the header on mount
  useEffect(() => {
    const fetchCurrent = async () => {
      try {
        const res = await api.get('/api/queue?no_rescore=true');
        setActiveQueueCount(res.data.length);
        setAlertsCount(res.data.filter(p => (p.risk_probability * 10) > 7.5).length);
      } catch (err) {
        console.error('Failed to fetch current queue:', err);
      }
    };
    fetchCurrent();
  }, []);

  const runTimeLapse = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/patients/timelapse?total_minutes=${horizon}&step_minutes=10`);
      
      // Transform backend snapshot data into Recharts friendly format
      const rawSnapshots = res.data;
      const namesSet = new Set();
      
      const transformed = rawSnapshots.map(snapshot => {
        const point = { t: snapshot.t };
        snapshot.patients.forEach(p => {
          point[p.name] = p.risk;
          namesSet.add(p.name);
        });
        return point;
      });

      setPatientNames(Array.from(namesSet));
      setChartData(transformed);
    } catch (err) {
      console.error('TimeLapse API failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const horizons = [60, 90, 120, 180];

  return (
    <div className="max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 flex flex-col h-screen overflow-hidden">
      <Header 
        currentPage="timelapse"
        setCurrentPage={setCurrentPage} 
        onSimulate={() => {}} 
        queueLength={activeQueueCount} 
        alertsCount={alertsCount}
        lastUpdated={Date.now()}
      />

      <div className="flex-1 overflow-y-auto pb-20 mt-4 pr-2">
        
        {/* Controls Section */}
        <div className="mb-8">
          <p className="text-gray-400 mb-6 max-w-4xl font-mono text-sm leading-relaxed">
            Visualise how patient risk trajectories evolve over time. The red dashed line at 7.5 is the alert threshold.
          </p>

          <div className="flex items-center gap-4">
            <span className="text-gray-500 font-mono text-sm tracking-widest">Horizon:</span>
            
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
              onClick={runTimeLapse}
              disabled={loading}
              className="px-6 py-2 ml-4 font-bold text-sm bg-[#e11d48] hover:bg-[#be123c] text-white rounded transition-colors flex items-center gap-2 shadow-lg disabled:opacity-50"
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</>
              ) : (
                <>Generate Curves</>
              )}
            </button>
          </div>
        </div>

        {/* Chart Section */}
        {chartData.length > 0 ? (
          <div className="bg-[#151923] border border-white/5 rounded-xl p-6 h-[500px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                <XAxis 
                  dataKey="t" 
                  stroke="#6b7280" 
                  tick={{ fill: '#6b7280', fontSize: 12 }} 
                  tickLine={false}
                  label={{ value: 'Minutes', position: 'bottom', fill: '#6b7280', fontSize: 12 }}
                />
                <YAxis 
                  domain={[0, 10]} 
                  stroke="#6b7280" 
                  tick={{ fill: '#6b7280', fontSize: 12 }} 
                  tickLine={false}
                  label={{ value: 'Risk', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 12 }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0b0f19', borderColor: '#ffffff20', color: '#fff', fontSize: '14px' }}
                  labelStyle={{ color: '#9ca3af', marginBottom: '8px' }}
                  labelFormatter={(val) => `Minute ${val}`}
                />
                <Legend 
                  wrapperStyle={{ paddingTop: '20px', fontSize: '13px' }}
                  iconType="circle"
                />
                <ReferenceLine 
                  y={7.5} 
                  stroke="#ef4444" 
                  strokeDasharray="5 5" 
                  label={{ value: "ALE", position: "right", fill: "#ef4444", fontSize: 12, fontWeight: 'bold' }} 
                />
                
                {patientNames.map((name, idx) => (
                  <Line 
                    key={name}
                    type="monotone" 
                    dataKey={name} 
                    stroke={COLORS[idx % COLORS.length]} 
                    strokeWidth={2}
                    dot={{ r: 3, strokeWidth: 2 }}
                    activeDot={{ r: 6 }}
                    isAnimationActive={true}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex-1 min-h-[400px] flex items-center justify-center font-mono text-sm text-gray-500">
            {loading ? 'Generating risk simulations...' : 'Click "Generate Curves" to render risk trajectories.'}
          </div>
        )}

      </div>
    </div>
  );
};

export default TimeLapse;
