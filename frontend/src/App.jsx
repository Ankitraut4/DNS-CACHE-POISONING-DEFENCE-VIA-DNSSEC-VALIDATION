import React, { useState, useEffect } from 'react';
import { Play, Square, Zap, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';

const API = 'http://localhost:5001/api';

function App() {
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [ip, setIp] = useState('');
  const [poisoned, setPoisoned] = useState(false);
  const [logs, setLogs] = useState('');
  const [metrics, setMetrics] = useState({ poison_attempts: 0, successful_poisons: 0, success_rate: 0,  blocked_attempts: 0 });
  const [dnssecStatus, setDnssecStatus] = useState(null);
  const [dnssecVerify, setDnssecVerify] = useState(null);
  const [authLogs, setAuthLogs] = useState(null);
  const [resolverLogs, setResolverLogs] = useState({ dnssec_logs: '', query_logs: '' });
  const [showDnssec, setShowDnssec] = useState(false);
  const [websiteData, setWebsiteData] = useState(null);
  const [showWebsite, setShowWebsite] = useState(true);

  useEffect(() => {
    if (running) {
      const interval = setInterval(() => {
        fetchLogs();
        fetchMetrics();
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [running]);

  const api = async (endpoint, method = 'GET') => {
    const res = await fetch(`${API}${endpoint}`, { method });
    return await res.json();
  };

  const startAttack = async () => {
    setLoading(true);
    await api('/attack/start', 'POST');
    setRunning(true);
    setLogs('Attack starting...\n');
    setTimeout(() => { fetchLogs(); queryDNS(); }, 10000); // Auto-check after 10s
    setLoading(false);
  };

  const stopAttack = async () => {
    await api('/attack/stop', 'POST');
    setRunning(false);
  };

  const queryDNS = async () => {
    setLoading(true);
    const data = await api('/query');
    setIp(data.ip);
    setPoisoned(data.poisoned);
    
    // Also fetch the website
    const websiteResp = await api('/website/fetch');
    setWebsiteData(websiteResp);
    
    setLoading(false);
  };

  const fetchWebsite = async () => {
    setLoading(true);
    const data = await api('/website/fetch');
    setWebsiteData(data);
    setIp(data.ip);
    setPoisoned(data.poisoned);
    setLoading(false);
  };

  const fetchLogs = async () => {
    const data = await api('/logs');
    setLogs(data.output);
  };

  const fetchMetrics = async () => {
    const data = await api('/metrics');
    setMetrics(data);
  };

  const reset = async () => {
    await api('/reset', 'POST');
    setRunning(false);
    setIp('');
    setPoisoned(false);
    setLogs('');
    setMetrics({ poison_attempts: 0, successful_poisons: 0, success_rate: 0 });
  };

  const setupDnssec = async () => {
    setLoading(true);
    try {
      const data = await api('/dnssec/setup', 'POST');
      if (data.success) {
        alert('✅ DNSSEC Setup Complete!\n\n' + data.output);
        await checkDnssecStatus();
      } else {
        alert('❌ DNSSEC Setup Failed:\n\n' + (data.error || data.output));
      }
    } catch (error) {
      alert('❌ Error: ' + error.message);
    }
    setLoading(false);
  };

  const checkDnssecStatus = async () => {
    const data = await api('/dnssec/status');
    setDnssecStatus(data);
  };

  const verifyDnssec = async () => {
    setLoading(true);
    const data = await api('/dnssec/verify');
    setDnssecVerify(data);
    setLoading(false);
  };

  const fetchAuthLogs = async () => {
    const data = await api('/dnssec/logs/authoritative');
    setAuthLogs(data.logs);
  };

  const fetchResolverLogs = async () => {
    const data = await api('/dnssec/logs/resolver');
    setResolverLogs(data);
  };

  const enableValidation = async () => {
    setLoading(true);
    try {
      const data = await api('/dnssec/enable-validation', 'POST');
      if (data.success) {
        alert('✅ DNSSEC Validation Enabled!\n\n' + data.output);
        await checkDnssecStatus();
        await verifyDnssec();
      } else {
        alert('❌ Failed to Enable Validation:\n\n' + (data.error || data.output));
      }
    } catch (error) {
      alert('❌ Error: ' + error.message);
    }
    setLoading(false);
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: '#fff', padding: '24px' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <h1 style={{ fontSize: '36px', marginBottom: '32px' }}>🛡️ DNS Cache Poisoning Lab</h1>

        {/* Controls */}
        <div style={{ background: '#1e293b', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
            <Btn onClick={startAttack} disabled={loading || running} icon={<Play size={20} />} color="#3b82f6">
              Start Attack
            </Btn>
            <Btn onClick={stopAttack} disabled={!running} icon={<Square size={20} />} color="#ef4444">
              Stop Attack
            </Btn>
            <Btn onClick={fetchWebsite} disabled={loading} icon={<Zap size={20} />} color="#8b5cf6">
              Load Website
            </Btn>
            <Btn onClick={reset} disabled={loading} color="#64748b">
              Reset
            </Btn>
          </div>
          
          <div style={{ fontSize: '14px', color: '#94a3b8' }}>
            Status: <span style={{ color: running ? '#ef4444' : '#64748b', fontWeight: 'bold' }}>
              {running ? '🔴 ATTACKING' : '⚪ STOPPED'}
            </span>
          </div>
        </div>

        {/* Website Viewer */}
        {websiteData && websiteData.success && (
          <div style={{ background: '#1e293b', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3>🌐 www.example.com</h3>
              <button onClick={() => setShowWebsite(!showWebsite)} style={{ padding: '8px 16px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                {showWebsite ? 'Hide Website' : 'Show Website'}
              </button>
            </div>
            
            <div style={{ marginBottom: '16px', padding: '12px', background: '#0f172a', borderRadius: '8px', fontSize: '14px' }}>
              <div style={{ marginBottom: '8px' }}>
                <strong>Resolved IP:</strong> <span style={{ color: websiteData.poisoned ? '#ef4444' : '#22c55e', fontFamily: 'monospace' }}>{websiteData.ip}</span>
              </div>
              <div style={{ marginBottom: '8px' }}>
                <strong>Website Type:</strong> <span style={{ color: websiteData.poisoned ? '#ef4444' : '#22c55e', textTransform: 'uppercase', fontWeight: 'bold' }}>
                  {websiteData.poisoned ? '🎣 FAKE PHISHING SITE' : '🏦 LEGITIMATE BANKING SITE'}
                </span>
              </div>
              <div>
                <strong>Port:</strong> <span style={{ color: '#94a3b8' }}>{websiteData.port}</span>
              </div>
            </div>

            {showWebsite && (
              <div style={{ border: websiteData.poisoned ? '4px solid #ef4444' : '4px solid #22c55e', borderRadius: '8px', overflow: 'hidden', background: '#fff' }}>
                <div style={{ background: websiteData.poisoned ? '#7f1d1d' : '#14532d', color: '#fff', padding: '12px', fontWeight: 'bold', textAlign: 'center' }}>
                  {websiteData.poisoned ? '⚠️ WARNING: FAKE PHISHING WEBSITE ⚠️' : '✅ SECURE: LEGITIMATE WEBSITE ✅'}
                </div>
                <iframe
                  srcDoc={websiteData.html}
                  style={{ width: '100%', height: '600px', border: 'none', background: '#fff' }}
                  title="Website Preview"
                  sandbox="allow-same-origin"
                />
              </div>
            )}
          </div>
        )}

        {/* Result */}
        {ip && (
          <div style={{ background: '#1e293b', padding: '24px', borderRadius: '12px', marginBottom: '24px', textAlign: 'center' }}>
            <div style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '12px' }}>www.example.com resolves to:</div>
            <div style={{ fontSize: '48px', fontWeight: 'bold', color: poisoned ? '#ef4444' : '#22c55e', fontFamily: 'monospace', marginBottom: '16px' }}>
              {ip}
            </div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '12px 24px', background: poisoned ? '#7f1d1d' : '#14532d', borderRadius: '8px' }}>
              {poisoned ? (
                <><AlertTriangle size={24} /> CACHE POISONED! Redirects to FAKE SITE</>
              ) : (
                <><CheckCircle size={24} /> Legitimate IP - REAL SITE</>
              )}
            </div>
            <div style={{ marginTop: '16px', fontSize: '14px', color: '#94a3b8' }}>
              {poisoned ? (
                <>🎣 Users visiting www.example.com will see the <strong style={{ color: '#ef4444' }}>FAKE phishing website</strong> at port 8081</>
              ) : (
                <>🏦 Users visiting www.example.com will see the <strong style={{ color: '#22c55e' }}>REAL website</strong> at port 8080</>
              )}
            </div>
          </div>
        )}

        {/* Metrics */}
        {running && metrics.poison_attempts > 0 && (
          <div style={{ background: '#1e293b', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '16px' }}>Metrics</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
              <Metric title="Poison Attempts" value={metrics.poison_attempts} color="#3b82f6" />
              <Metric title="Successful Poisons" value={metrics.successful_poisons} color="#22c55e" />
              <Metric title="Blocked by DNSSEC" value={metrics.blocked_attempts} color="#c52222ff "/>
              <Metric title="Success Rate" value={`${metrics.success_rate}%`} color="#f59e0b" />
            </div>
          </div>
        )}

        {/* Logs */}
        <div style={{ background: '#1e293b', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3>🔐 DNSSEC Security</h3>
            <button onClick={() => setShowDnssec(!showDnssec)} style={{ padding: '8px 16px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
              {showDnssec ? 'Hide' : 'Show'} DNSSEC Panel
            </button>
          </div>

          {showDnssec && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '16px' }}>
                <Btn onClick={setupDnssec} disabled={loading} color="#6366f1">
                  {dnssecStatus && dnssecStatus.zone_signed ? 'Turn DNSSEC OFF' : 'Setup DNSSEC'}
                </Btn>
                <Btn onClick={checkDnssecStatus} disabled={loading} color="#8b5cf6">
                  Check Status
                </Btn>
                <Btn onClick={enableValidation} disabled={loading} color="#10b981">
                  Enable Validation
                </Btn>
                <Btn onClick={verifyDnssec} disabled={loading} color="#ec4899">
                  Verify Signatures
                </Btn>
                <Btn onClick={() => { fetchAuthLogs(); fetchResolverLogs(); }} disabled={loading} color="#0891b2" style={{ gridColumn: 'span 2' }}>
                  Fetch Logs
                </Btn>
              </div>

              {dnssecStatus && (
                <div style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                  <h4 style={{ marginBottom: '12px', color: '#94a3b8' }}>DNSSEC Status</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', fontSize: '14px' }}>
                    <div style={{ color: dnssecStatus.zone_signed ? '#22c55e' : '#ef4444' }}>
                      {dnssecStatus.zone_signed ? '✅' : '❌'} Zone Signed
                    </div>
                    <div style={{ color: dnssecStatus.keys_generated ? '#22c55e' : '#ef4444' }}>
                      {dnssecStatus.keys_generated ? '✅' : '❌'} Keys Generated
                    </div>
                    <div style={{ color: dnssecStatus.dnskey_records ? '#22c55e' : '#ef4444' }}>
                      {dnssecStatus.dnskey_records ? '✅' : '❌'} DNSKEY Records
                    </div>
                    <div style={{ color: dnssecStatus.dnssec_enabled ? '#22c55e' : '#ef4444' }}>
                      {dnssecStatus.dnssec_enabled ? '✅' : '❌'} DNSSEC Enabled
                    </div>
                  </div>
                </div>
              )}

              {dnssecVerify && (
                <div style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                  <h4 style={{ marginBottom: '12px', color: '#94a3b8' }}>DNSSEC Verification for {dnssecVerify.domain}</h4>
                  <div style={{ marginBottom: '12px', fontSize: '14px' }}>
                    <div style={{ color: dnssecVerify.authenticated ? '#22c55e' : '#ef4444', marginBottom: '4px' }}>
                      {dnssecVerify.authenticated ? '✅' : '❌'} Authenticated Data (AD flag)
                    </div>
                    <div style={{ color: dnssecVerify.has_signatures ? '#22c55e' : '#ef4444', marginBottom: '4px' }}>
                      {dnssecVerify.has_signatures ? '✅' : '❌'} RRSIG Records Present
                    </div>
                    <div style={{ color: dnssecVerify.validation_successful ? '#22c55e' : '#ef4444', fontWeight: 'bold' }}>
                      {dnssecVerify.validation_successful ? '✅ DNSSEC VALIDATION SUCCESSFUL' : '❌ DNSSEC VALIDATION FAILED'}
                    </div>
                  </div>
                  <pre style={{ background: '#000', padding: '12px', borderRadius: '6px', color: '#22c55e', fontSize: '12px', maxHeight: '200px', overflow: 'auto', fontFamily: 'monospace' }}>
                    {dnssecVerify.query_output}
                  </pre>
                </div>
              )}

              {authLogs!==null && (
                <div style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                  <h4 style={{ marginBottom: '12px', color: '#94a3b8' }}>📋 Authoritative Server DNSSEC Logs</h4>
                  <pre style={{ background: '#000', padding: '12px', borderRadius: '6px', color: '#22c55e', fontSize: '12px', maxHeight: '200px', overflow: 'auto', fontFamily: 'monospace' }}>
                    {authLogs}
                  </pre>
                </div>
              )}

              {resolverLogs.dnssec_logs && (
                <div style={{ background: '#0f172a', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
                  <h4 style={{ marginBottom: '12px', color: '#94a3b8' }}>🔍 Resolver DNSSEC Validation Logs</h4>
                  <pre style={{ background: '#000', padding: '12px', borderRadius: '6px', color: '#22c55e', fontSize: '12px', maxHeight: '200px', overflow: 'auto', fontFamily: 'monospace' }}>
                    {resolverLogs.dnssec_logs}
                  </pre>
                  <h4 style={{ marginTop: '12px', marginBottom: '12px', color: '#94a3b8' }}>📝 Recent DNS Queries</h4>
                  <pre style={{ background: '#000', padding: '12px', borderRadius: '6px', color: '#3b82f6', fontSize: '12px', maxHeight: '200px', overflow: 'auto', fontFamily: 'monospace' }}>
                    {resolverLogs.query_logs}
                  </pre>
                </div>
              )}
            </>
          )}
        </div>

      </div>
    </div>
  );
}

const Btn = ({ onClick, disabled, icon, color, children }) => (
  <button onClick={onClick} disabled={disabled} style={{ padding: '12px 24px', background: color, color: '#fff', border: 'none', borderRadius: '8px', cursor: disabled ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '8px', opacity: disabled ? 0.5 : 1 }}>
    {icon}{children}
  </button>
);

const Metric = ({ title, value, color }) => (
  <div style={{ background: '#0f172a', padding: '20px', borderRadius: '8px' }}>
    <div style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '8px' }}>{title}</div>
    <div style={{ fontSize: '32px', fontWeight: 'bold', color }}>{value}</div>
  </div>
);

export default App;