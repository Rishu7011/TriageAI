import { useState, useEffect } from 'react';
import api from '../services/api';

export const useQueue = () => {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(Date.now());

  const fetchQueue = async (noRescore = false) => {
    // If it's an event object (from a button click), it means noRescore wasn't explicitly set to boolean true.
    const isNoRescore = noRescore === true;
    
    try {
      const response = await api.get(`/api/queue?no_rescore=${isNoRescore}`);
      // Set sorted queue by risk score descending, assuming backend might not be sorted or to be safe
      const sorted = response.data.sort((a, b) => b.risk_score - a.risk_score);
      setQueue(sorted);
      if (!isNoRescore) {
        setLastUpdated(Date.now());
      }
      setError(null);
    } catch (err) {
      setError(err);
      console.error('Error fetching queue:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue(true); // Initial fetch without rescoring
    const intervalId = setInterval(() => fetchQueue(false), 60000); // 1 minute interval WITH rescore
    return () => clearInterval(intervalId);
  }, []);

  return { queue, loading, error, refetch: fetchQueue, lastUpdated };
};
