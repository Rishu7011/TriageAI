import { useEffect, useRef, useLayoutEffect } from 'react';
import gsap from 'gsap';
import { Flip } from 'gsap/Flip';
import PatientCard from './PatientCard';

gsap.registerPlugin(Flip);

const Queue = ({ patients, onSelectPatient, selectedPatient }) => {
  const containerRef = useRef();

  useLayoutEffect(() => {
    if (!containerRef.current || !patients.length) return;
    
    // Get the state of the elements before they change
    const cards = gsap.utils.toArray('.patient-card');
    const state = Flip.getState(cards);

    // After state change, React renders, then this hook fires again.
    // In React 18 strict mode, useLayoutEffect may fire twice, but Flip handles it gracefully.
    // GSAP flip reorders it smoothly.
    Flip.from(state, {
      duration: 0.4,
      ease: "power2.out",
      absolute: true,
      fade: true,
      stagger: 0.05,
      scale: true
    });
  }, [patients]); // re-run when patients array changes (e.g. order change)

  return (
    <div className="flex flex-col h-full bg-[#0b0f19] rounded-2xl border border-white/5 overflow-hidden">
      <div className="p-5 border-b border-white/5 bg-[#0b0f19] sticky top-0 z-10 flex flex-col gap-2">
        <h2 className="text-xl font-bold text-white flex items-center justify-between">
          Active Queue
        </h2>
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-gray-500 font-bold tracking-widest uppercase">
            Sorted by Algorithmic Risk Score
          </span>
          <div className="flex items-center gap-4 text-[10px] font-bold text-gray-400 tracking-wider">
             <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span> CRITICAL</div>
             <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-yellow-500 rounded-full"></span> HIGH RISK</div>
             <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span> STABLE</div>
          </div>
        </div>
      </div>

      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 relative"
      >
        {patients.map(patient => (
          <div key={patient.patient_id} className="patient-card" data-flip-id={patient.patient_id}>
            <PatientCard 
              patient={patient} 
              isActive={selectedPatient?.patient_id === patient.patient_id}
              onClick={onSelectPatient}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default Queue;
