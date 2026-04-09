import { useState, useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import WhatIf from './pages/WhatIf';
import TimeLapse from './pages/TimeLapse';
import { loadDemoData } from './services/api';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');

  // Hard refresh reset: Wipes any custom-admitted patients and resets backend to 10 demo patients
  useEffect(() => {
    loadDemoData().catch(console.error);
  }, []);

  return (
    <div className="min-h-screen bg-[#0b0f19] text-gray-200">
      {(currentPage === 'dashboard' || currentPage === 'patient-queue') ? (
        <Dashboard setCurrentPage={setCurrentPage} />
      ) : currentPage === 'whatif' ? (
        <WhatIf setCurrentPage={setCurrentPage} />
      ) : (
        <TimeLapse setCurrentPage={setCurrentPage} />
      )}
    </div>
  );
}

export default App;
