import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

export const useAlerts = () => {
  const [activeAlert, setActiveAlert] = useState(null);

  const clearAlert = useCallback(() => {
    setActiveAlert(null);
  }, []);

  const fetchAlerts = async () => {
    try {
      const response = await api.get('/api/alerts');
      const criticalAlerts = response.data.filter(alert => alert.severity === 'critical');
      
      if (criticalAlerts.length > 0) {
        // Just take the first critical alert for now
        setActiveAlert(criticalAlerts[0]);
        // Auto dismiss after 30 seconds
        setTimeout(() => {
          setActiveAlert(null);
        }, 30000);
      }
    } catch (err) {
      console.error('Error fetching alerts:', err);
    }
  };

  useEffect(() => {
    fetchAlerts();
    const intervalId = setInterval(fetchAlerts, 10000);
    return () => clearInterval(intervalId);
  }, []);

  return { activeAlert, clearAlert };
};
