import { useEffect, useRef } from 'react';
import { AlertCircle, X } from 'lucide-react';
import gsap from 'gsap';

const AlertBanner = ({ alert, onClose }) => {
  const bannerRef = useRef(null);

  useEffect(() => {
    if (alert) {
      gsap.fromTo(bannerRef.current, 
        { y: -50, opacity: 0, scale: 0.95 }, 
        { y: 0, opacity: 1, scale: 1, duration: 0.5, ease: 'power3.out' }
      );
    }
  }, [alert]);

  const handleClose = () => {
    if (bannerRef.current) {
      gsap.to(bannerRef.current, {
        y: -50, opacity: 0, scale: 0.95, duration: 0.4, ease: 'power3.in',
        onComplete: onClose
      });
    } else {
      onClose();
    }
  };

  if (!alert) return null;

  return (
    <div 
      ref={bannerRef}
      className="mb-4 bg-[#b91c1c] rounded-xl flex flex-col p-6 z-40 relative shadow-[0_5px_30px_rgba(185,28,28,0.2)]"
    >
      <div className="flex items-center gap-2 mb-4 text-white text-[11px] font-bold tracking-widest uppercase">
        <AlertCircle className="w-4 h-4 fill-white text-[#b91c1c]" /> RED ZONE ALERT
      </div>
      
      <h3 className="text-white font-bold text-xl leading-tight mb-3 uppercase shadow-sm">
        Deterioration Detected:<br/> {alert.patient_name || 'Patient'}
      </h3>
      
      <p className="text-red-100 text-sm mb-6 leading-relaxed">
        {alert.message || 'Severe physiological deterioration flagged. Requires immediate clinical review based on recent continuous vitals assessment.'}
      </p>

      <div className="flex flex-col gap-3">
        <button 
          onClick={handleClose}
          className="w-full bg-white text-[#b91c1c] hover:bg-gray-100 py-3 rounded text-sm font-bold tracking-wider uppercase transition-colors"
        >
          Acknowledge Alert
        </button>
        <button 
          onClick={handleClose} // Placeholder for escalate
          className="w-full bg-orange-500 hover:bg-orange-400 text-white py-3 rounded text-sm font-bold tracking-wider uppercase transition-colors shadow-[0_0_15px_rgba(249,115,22,0.4)]"
        >
          Escalate to Senior Physician
        </button>
      </div>

      <div className="mt-4 text-center">
        <button className="text-red-200 hover:text-white text-xs font-bold tracking-widest uppercase transition-colors">
          View Full Analytics Report
        </button>
      </div>
      
      {/* Visual background element */}
      <div className="absolute right-0 bottom-0 text-red-900/20 text-9xl font-black italic -mr-4 -mb-4 pointer-events-none select-none">!</div>
    </div>
  );
};

export default AlertBanner;
