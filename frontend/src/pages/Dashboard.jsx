import { useState } from 'react';
import Header from '../components/Header';
import AlertBanner from '../components/AlertBanner';
import Queue from '../components/Queue';
import ShapChart from '../components/ShapChart';
import EmptyState from '../components/EmptyState';
import AdmitPatientForm from '../components/AdmitPatientForm';
import SimulationBar from '../components/SimulationBar';
import { useQueue } from '../hooks/useQueue';
import { useAlerts } from '../hooks/useAlerts';
import { simulateTime, loadDemoData } from '../services/api';

const Dashboard = ({ setCurrentPage }) => {
  const { queue, loading: queueLoading, refetch, lastUpdated } = useQueue();
  const { activeAlert, clearAlert } = useAlerts();
  
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const handleSimulate = async (action) => {
    try {
      setIsSimulating(true);
      if (action === 'demo') {
        await loadDemoData();
      } else {
        await simulateTime(action); // action is minutes here
      }
      await refetch();
    } catch (err) {
      console.error('Simulation failed:', err);
    } finally {
      setIsSimulating(false);
    }
  };

  // Auto-select first patient if none selected and queue loads
  if (!selectedPatient && queue.length > 0) {
    setSelectedPatient(queue[0]);
  }

  const showEmptyState = queue.length === 0 && !queueLoading;

  if (showEmptyState && !isSimulating) {
    return (
      <div className="flex flex-col min-h-screen">
        <EmptyState onLoadDemo={() => handleSimulate('demo')} />
      </div>
    );
  }

  return (
    <div className="max-w-[1600px] w-full mx-auto px-4 sm:px-6 lg:px-8 flex flex-col h-screen overflow-hidden relative pb-[80px]">
      <Header 
        currentPage="dashboard"
        setCurrentPage={setCurrentPage}
        onSimulate={handleSimulate} 
        onRescore={refetch}
        queueLength={queue.length} 
        alertsCount={queue.filter(p => (p.risk_probability * 10) > 7.5).length} 
        lastUpdated={lastUpdated}
      />
      
      {isSimulating && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="glass p-8 rounded-2xl flex flex-col items-center">
            <div className="w-12 h-12 border-4 border-red-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <h2 className="text-xl font-bold text-white">Processing...</h2>
            <p className="text-gray-400 mt-2">Loading data</p>
          </div>
        </div>
      )}

      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <AlertBanner alert={activeAlert} onClose={clearAlert} />

        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-4 pb-6">
          {/* Left Column - Admit Form */}
          <div className="hidden lg:block lg:col-span-3 min-h-0 h-full rounded-2xl overflow-hidden border border-white/5">
            <AdmitPatientForm onAdmitSuccess={refetch} />
          </div>

          {/* Center Column - Queue */}
          <div className="lg:col-span-5 min-h-0 h-full relative">
            {queueLoading ? (
              <div className="h-full bg-[#151923] rounded-2xl flex items-center justify-center border border-white/5">
                <div className="w-8 h-8 border-4 border-red-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : (
              <Queue 
                patients={queue} 
                selectedPatient={selectedPatient}
                onSelectPatient={setSelectedPatient} 
              />
            )}
          </div>

          {/* Right Column - Details & SHAP */}
          <div className="lg:col-span-4 min-h-0 h-full flex flex-col gap-4 overflow-y-auto pr-2 pb-20">
            {selectedPatient ? (
              <>
                <div className="glass p-8 shrink-0 rounded-2xl border border-white/5 shadow-2xl relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/10 rounded-full blur-3xl -mr-32 -mt-32 transition-transform group-hover:scale-110"></div>
                  
                  <h2 className="text-3xl font-bold text-white mb-2">{selectedPatient.name || `Patient #${String(selectedPatient.patient_id || '').slice(0, 4)}`}</h2>
                  <div className="flex gap-4 text-sm text-gray-400 mb-8">
                    <span>{selectedPatient.age || 'N/A'} years old</span>
                    <span>•</span>
                    <span>Gender: {selectedPatient.sex || 'Unknown'}</span>
                    <span>•</span>
                    <span>Arrival: {selectedPatient.arrival_time ? new Date(selectedPatient.arrival_time).toLocaleTimeString() : 'N/A'}</span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    <div className="bg-gray-900/50 p-4 rounded-xl border border-white/5">
                      <p className="text-sm text-gray-400 mb-1">Risk Score</p>
                      <p className="text-2xl font-bold text-red-400">{((selectedPatient.risk_probability || 0) * 10).toFixed(1)}</p>
                    </div>
                    <div className="bg-gray-900/50 p-4 rounded-xl border border-white/5">
                      <p className="text-sm text-gray-400 mb-1">Heart Rate</p>
                      <p className="text-2xl font-bold text-white">{selectedPatient.hr || 0} <span className="text-sm font-normal text-gray-500">bpm</span></p>
                    </div>
                    <div className="bg-gray-900/50 p-4 rounded-xl border border-white/5">
                      <p className="text-sm text-gray-400 mb-1">Blood Pressure</p>
                      <p className="text-2xl font-bold text-white">{selectedPatient.sbp || 0}/{selectedPatient.dbp || 0} <span className="text-sm font-normal text-gray-500">mmHg</span></p>
                    </div>
                    <div className="bg-gray-900/50 p-4 rounded-xl border border-white/5">
                      <p className="text-sm text-gray-400 mb-1">O2 Saturation</p>
                      <p className="text-2xl font-bold text-white">{selectedPatient.spo2 || 0}%</p>
                    </div>
                  </div>
                </div>

                <ShapChart labels={selectedPatient.shap_labels} values={selectedPatient.shap_values} />
              </>
            ) : (
              <div className="h-[400px] glass rounded-2xl flex items-center justify-center text-gray-500 border border-white/5">
                Select a patient from the queue to view details
              </div>
            )}
          </div>
        </div>
      </main>

      <SimulationBar onSimulate={handleSimulate} />
    </div>
  );
};

export default Dashboard;
