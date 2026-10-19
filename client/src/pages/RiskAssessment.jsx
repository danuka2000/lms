import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { RefreshCw, X } from 'lucide-react';

const API_URL = import.meta.env.VITE_PYTHON_BACKEND || 'http://localhost:3000';

const metricRows = [
    { key: 'quiz_score', label: 'Quiz Score', suffix: '%' },
    { key: 'assignment_score', label: 'Assignment Score', suffix: '%' },
    { key: 'study_hours', label: 'Study Hours', suffix: ' hrs' },
    { key: 'late_assignments', label: 'Late Assignments' },
    { key: 'completed_assignments', label: 'Completed Assignments' },
];
const metricByKey = Object.fromEntries(metricRows.map((metric) => [metric.key, metric]));

const formatMetric = (value, suffix = '') => {
    if (value === null || value === undefined || value === '') return '—';
    const number = Number(value);
    const formatted = Number.isFinite(number)
        ? number.toLocaleString(undefined, { maximumFractionDigits: 2 })
        : value;
    return `${formatted}${suffix}`;
};

const RiskAssessment = () => {
    const [assessments, setAssessments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [currentUserId, setCurrentUserId] = useState('');
    const [selectedAssessment, setSelectedAssessment] = useState(null);

    const loadAssessments = async () => {
        setLoading(true);
        setError('');
        try {
            const token = localStorage.getItem('token');
            if (!token) throw new Error('Sign in to view your risk assessment.');
            const { data } = await axios.get(`${API_URL}/api/risk-assessment`, {
                headers: { 'x-auth-token': token },
            });
            const userId = String(data.user_id || '');
            if (!userId) {
                throw new Error('The Python service is outdated. Restart it to enable account-specific risk results.');
            }
            setCurrentUserId(userId);
            setAssessments((data.assessments || []).filter((item) => String(item.user_id) === userId));
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Could not load assessments. Check that the Python service is running on port 3000.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadAssessments(); }, []);

    useEffect(() => {
        if (!selectedAssessment) return undefined;
        const closeOnEscape = (event) => {
            if (event.key === 'Escape') setSelectedAssessment(null);
        };
        document.addEventListener('keydown', closeOnEscape);
        return () => document.removeEventListener('keydown', closeOnEscape);
    }, [selectedAssessment]);

    return (
        <div className="risk-page">
            <div className="risk-heading">
                <div>
                    <p>Review at-risk modules for your enrolled subjects.</p>
                </div>
                <button className="refresh-button" onClick={loadAssessments} disabled={loading}>
                    <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
                </button>
            </div>

            {error ? (
                <div className="notice error-notice">
                    <strong>Assessment unavailable</strong>
                    <span>{error}</span>
                    <small>Confirm the training and manual input CSV files are in python/data, then restart the Python service.</small>
                </div>
            ) : loading ? (
                <div className="page-message">Loading risk assessments...</div>
            ) : assessments.length === 0 ? (
                <div className="page-message">No at-risk modules found for your account. Set <code>user_id</code> on your module rows in <code>python/data/manual_risk_inputs.csv</code> to <code>{currentUserId || 'unavailable'}</code>, then refresh.</div>
            ) : (
                <section className="modules-section">
                    <div className="section-heading">
                        <h2>Risk Modules</h2>
                        <span>{assessments.length} module{assessments.length === 1 ? '' : 's'}</span>
                    </div>
                    <div className="module-grid">
                        {assessments.map((item, index) => (
                            <button
                                className="module-card"
                                key={`${item.student_id}-${item.module_id}-${index}`}
                                onClick={() => setSelectedAssessment(item)}
                                aria-label={`View ${item.module_id} ${item.module_name}, ${item.risk_level} risk details`}
                            >
                                <span className="module-code">{item.module_id}</span>
                                <strong className="module-name">{item.module_name}</strong>
                                <span className={`risk-badge ${String(item.risk_level).toLowerCase()}`}>
                                    <i />{item.risk_level} Risk
                                </span>
                            </button>
                        ))}
                    </div>
                </section>
            )}

            {selectedAssessment && (
                <div className="modal-overlay" onMouseDown={(event) => {
                    if (event.target === event.currentTarget) setSelectedAssessment(null);
                }}>
                    <section className="risk-modal" role="dialog" aria-modal="true" aria-labelledby="risk-modal-title">
                        <div className="modal-heading">
                            <div>
                                <span className="modal-module-code">{selectedAssessment.module_id} · {selectedAssessment.module_name}</span>
                                <h2 id="risk-modal-title">Student Risk</h2>
                                <p>{selectedAssessment.student_name} · {selectedAssessment.student_id}</p>
                            </div>
                            <button className="close-button" onClick={() => setSelectedAssessment(null)} aria-label="Close risk details">
                                <X size={20} />
                            </button>
                        </div>
                        {selectedAssessment.risk_factors?.length ? (
                            <div className="metric-grid">
                                {selectedAssessment.risk_factors.map((factor) => {
                                    const metric = metricByKey[factor.key];
                                    if (!metric) return null;
                                    return (
                                        <div className="metric-card" key={factor.key}>
                                            <span>{factor.label || metric.label}</span>
                                            <strong>{formatMetric(factor.value, metric.suffix)}</strong>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <p className="no-risk-factors">The model identified risk from a combination of indicators; no individual weak area stood out against the training data.</p>
                        )}
                    </section>
                </div>
            )}

            <style>{`
                .risk-page{max-width:1400px;margin:0 auto;padding:8px 0 30px;color:#202b36}.risk-heading{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:26px}.eyebrow{font-size:11px;letter-spacing:1.2px;font-weight:700;color:#328767}.risk-heading h1{font-size:28px;margin:8px 0;color:#213238}.risk-heading p{margin:0;color:#71808a;font-size:14px}.refresh-button{display:flex;align-items:center;gap:8px;border:1px solid #dce5e3;background:white;border-radius:10px;padding:10px 14px;color:#2d5550;font-weight:600;cursor:pointer}.refresh-button:disabled{opacity:.65}.modules-section{background:#fff;border:1px solid #edf0f1;border-radius:16px;padding:22px;box-shadow:0 3px 14px rgba(33,50,56,.035)}.section-heading{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}.section-heading h2{font-size:17px;margin:0;color:#293b40}.section-heading span{color:#829096;font-size:13px}.module-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(235px,1fr));gap:14px}.module-card{appearance:none;text-align:left;display:flex;flex-direction:column;align-items:flex-start;gap:13px;min-height:142px;padding:18px;background:#fff;border:1px solid #e8eeee;border-radius:13px;box-shadow:0 3px 12px rgba(33,50,56,.035);cursor:pointer;transition:border-color .15s,transform .15s,box-shadow .15s}.module-card:hover{border-color:#a9cfc0;transform:translateY(-2px);box-shadow:0 8px 20px rgba(33,50,56,.08)}.module-card:focus-visible,.close-button:focus-visible{outline:3px solid #8ccbb0;outline-offset:2px}.module-code{font-size:11px;letter-spacing:.8px;font-weight:700;color:#70818a}.module-name{font-size:16px;line-height:1.35;color:#293a40}.risk-badge{display:inline-flex;align-items:center;gap:6px;border-radius:20px;padding:6px 9px;font-size:11px;font-weight:700}.risk-badge i{width:6px;height:6px;border-radius:50%;background:currentColor}.risk-badge.high{color:#bd493b;background:#fff0ed}.risk-badge.medium{color:#a97513;background:#fff6e3}.page-message{padding:48px 20px;text-align:center;color:#71808a;font-size:14px;background:#fff;border:1px solid #edf0f1;border-radius:15px}.notice{margin:20px 0;padding:16px;border-radius:10px;display:grid;gap:6px;font-size:13px}.notice.error-notice{background:#fff5f3;color:#9d4439}.notice small{color:#7c6662}.data-note{padding:14px 2px;color:#829096;font-size:11px}.modal-overlay{position:fixed;inset:0;z-index:1000;display:grid;place-items:center;padding:22px;background:rgba(24,38,43,.48);backdrop-filter:blur(3px)}.risk-modal{width:min(620px,100%);max-height:min(88vh,760px);overflow:auto;background:#fff;border-radius:18px;padding:25px;box-shadow:0 24px 80px rgba(18,32,36,.25)}.modal-heading{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;padding-bottom:18px;border-bottom:1px solid #edf0f1}.modal-module-code{font-size:12px;color:#74838a;font-weight:600}.modal-heading h2{font-size:23px;margin:9px 0 4px;color:#213238}.modal-heading p{margin:0;color:#71808a;font-size:13px}.close-button{display:grid;place-items:center;width:36px;height:36px;border:0;border-radius:9px;background:#f5f7f7;color:#627178;cursor:pointer}.metric-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding-top:18px}.metric-card{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:13px 14px;border:1px solid #edf0f1;border-radius:10px;background:#fafbfb}.metric-card span{font-size:12px;color:#74818a}.metric-card strong{font-size:14px;color:#293a40;white-space:nowrap}.no-risk-factors{margin:18px 0 0;padding:14px;border:1px solid #edf0f1;border-radius:10px;background:#fafbfb;color:#71808a;font-size:13px;line-height:1.5}.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
                @media(max-width:620px){.risk-heading{align-items:flex-start}.risk-heading h1{font-size:23px}.modules-section{padding:16px}.module-grid{grid-template-columns:1fr}.risk-modal{padding:20px}.metric-grid{grid-template-columns:1fr}.metric-card{padding:12px}}
            `}</style>
        </div>
    );
};

export default RiskAssessment;
