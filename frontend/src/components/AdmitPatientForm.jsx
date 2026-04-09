import { useState } from 'react';
import { UserPlus, Plus } from 'lucide-react';
import { admitPatient } from '../services/api';

const AdmitPatientForm = ({ onAdmitSuccess }) => {
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    sex: 'Male',
    chief_complaint: '',
    hr: '',
    bp: '', // e.g. 120/80
    spo2: '',
    temp: '',
    symptom_category: 'Chest Pain / Cardiac', // Needs to precisely match python dict
    has_comorbidity: false
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    
    try {
      // Parse BP
      const [sbpStr, dbpStr] = formData.bp.split('/');
      const sbp = parseInt(sbpStr) || 120;
      const dbp = parseInt(dbpStr) || 80;

      const payload = {
        name: formData.name || 'Unknown Patient',
        age: parseInt(formData.age) || 45,
        sex: formData.sex,
        symptom_category: formData.symptom_category,
        chief_complaint: formData.chief_complaint || 'N/A',
        hr: parseFloat(formData.hr) || 80,
        sbp: sbp,
        dbp: dbp,
        rr: 16, // Default since not in mock
        spo2: parseFloat(formData.spo2) || 98,
        temp: parseFloat(formData.temp) || 98.6,
        has_comorbidity: formData.has_comorbidity
      };

      await admitPatient(payload);
      
      // Reset form on success
      setFormData({
        name: '', age: '', sex: 'Male', chief_complaint: '',
        hr: '', bp: '', spo2: '', temp: '', symptom_category: 'Cardiac', has_comorbidity: false
      });
      
      if (onAdmitSuccess) onAdmitSuccess();
      
    } catch (err) {
      console.error(err);
      setError('Failed to admit patient');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  return (
    <div className="bg-[#151923] border-r border-white/5 h-full p-6 flex flex-col overflow-y-auto">
      <div className="flex items-center gap-2 text-gray-300 font-medium text-sm tracking-widest uppercase mb-8">
        <UserPlus className="w-4 h-4" /> Admit Patient
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5 flex-1">
        
        {/* Full Name */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-gray-500 tracking-wider uppercase">Full Name</label>
          <input 
            required
            name="name" value={formData.name} onChange={handleChange}
            placeholder="e.g. John Doe"
            className="bg-[#1e2336] border border-white/10 rounded-md px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-all"
          />
        </div>

        {/* Age and Sex Row */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 tracking-wider uppercase">Age</label>
            <input 
              required type="number" min="1" max="120"
              name="age" value={formData.age} onChange={handleChange}
              className="bg-[#1e2336] border border-white/10 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500 transition-all"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 tracking-wider uppercase">Sex</label>
            <select 
              name="sex" value={formData.sex} onChange={handleChange}
              className="bg-[#1e2336] border border-white/10 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500 transition-all appearance-none"
            >
              <option>Male</option>
              <option>Female</option>
              <option>Other</option>
            </select>
          </div>
        </div>

        {/* Chief Complaint */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-gray-500 tracking-wider uppercase">Chief Complaint</label>
          <textarea 
            required
            name="chief_complaint" value={formData.chief_complaint} onChange={handleChange}
            placeholder="Primary reason for visit..."
            className="bg-[#1e2336] border border-white/10 rounded-md px-3 py-2 text-sm text-white placeholder-gray-600 min-h-[80px] resize-none focus:outline-none focus:border-red-500 transition-all"
          />
        </div>

        {/* Vitals Grid Row 1 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 tracking-wider uppercase">HR (bpm)</label>
            <input 
              required type="number" min="0" max="300"
              name="hr" value={formData.hr} onChange={handleChange}
              className="bg-[#1e2336] border border-white/10 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500 transition-all"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 tracking-wider uppercase">BP (mmHg)</label>
            <input 
              required
              name="bp" value={formData.bp} onChange={handleChange} placeholder="120/80"
              className="bg-[#1e2336] border border-white/10 rounded-md px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-red-500 transition-all"
            />
          </div>
        </div>

        {/* Vitals Grid Row 2 */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 tracking-wider uppercase">SpO2 (%)</label>
            <input 
              required type="number" min="0" max="100"
              name="spo2" value={formData.spo2} onChange={handleChange}
              className="bg-[#1e2336] border border-white/10 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500 transition-all"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-gray-500 tracking-wider uppercase">Temp (°F)</label>
            <input 
              required type="number" min="80" max="115" step="0.1"
              name="temp" value={formData.temp} onChange={handleChange}
              className="bg-[#1e2336] border border-white/10 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500 transition-all"
            />
          </div>
        </div>

        {/* Comorbidities simple mapping */}
        <div className="flex flex-col gap-2 mt-2">
          <label className="text-xs font-bold text-gray-500 tracking-wider uppercase">Comorbidities</label>
          <div className="flex items-center gap-2">
             <label className="bg-[#1e2336] border border-white/10 rounded-full px-3 py-1 flex items-center gap-2 cursor-pointer hover:bg-white/5">
                <input type="checkbox" name="has_comorbidity" checked={formData.has_comorbidity} onChange={handleChange} className="accent-red-500" />
                <span className="text-xs text-gray-300">Has major comorbidity</span>
             </label>
          </div>
        </div>

        {error && <div className="text-red-400 text-xs">{error}</div>}

        <div className="mt-auto pt-6">
          <button 
            type="submit" disabled={isSubmitting}
            className="w-full py-3 bg-[#10b981] hover:bg-[#059669] disabled:opacity-50 text-white rounded-lg font-bold transition-colors shadow-[0_0_20px_rgba(16,185,129,0.3)] flex justify-center items-center gap-2"
          >
            {isSubmitting ? 'Admitting...' : <> <UserPlus className="w-5 h-5 fill-current" /> Admit to ED</>}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AdmitPatientForm;
