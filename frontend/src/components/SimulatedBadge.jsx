import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export default function SimulatedBadge() {
  const [status, setStatus] = useState({
    status: 'ACTIVE',
    indicator: 'green',
    last_tick_at: new Date().toLocaleTimeString('en-IN')
  });

  useEffect(() => {
    let mounted = true;
    const fetchStatus = () => {
      api.market.getStatus()
        .then(res => {
          if (mounted && res.ok) {
            setStatus({
              status: res.data.status,
              indicator: res.data.indicator || 'green',
              last_tick_at: res.data.last_tick_at 
                ? new Date(res.data.last_tick_at).toLocaleTimeString('en-IN')
                : new Date().toLocaleTimeString('en-IN')
            });
          }
        })
        .catch(() => {
          if (mounted) {
            setStatus(prev => ({ ...prev, indicator: 'red' }));
          }
        });
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const dotClass = status.indicator === 'green' ? 'pulse-green' : (status.indicator === 'amber' ? 'pulse-amber' : 'pulse-red');

  return (
    <div className="badge badge-simulated" title={`Market Simulator: ${status.status}`}>
      <span className={`pulse-dot ${dotClass}`} />
      <span>SIMULATED MARKET DATA · last update {status.last_tick_at}</span>
    </div>
  );
}
