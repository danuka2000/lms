import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { AlertTriangle, BookOpen, RefreshCw, Search, Users } from 'lucide-react';

const API_URL = import.meta.env.VITE_PYTHON_BACKEND || 'http://localhost:3000';

const RiskAssessment = () => {
    const [assessments, setAssessments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [query, setQuery] = useState('');

    const loadAssessments = async () => {
        setLoading(true);
        setError('');
        try {
            const { data } = await axios.get(`${API_URL}/api/risk-assessment`);
            setAssessments(data.assessments || []);
        } catch (err) {
            setError(err.response?.data?.error || 'Could not load assessments. Check that the Python service is running on port 3000.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadAssessments(); }, []);

    const filtered = useMemo(() => {
        const term = query.trim().toLowerCase();
        if (!term) return assessments;
        return assessments.filter((item) => [item.student_id, item.student_name, item.module_id, item.module_name, item.risk_level].some((value) => String(value).toLowerCase().includes(term)));
    }, [assessments, query]);

    const highRiskCount = assessments.filter((item) => item.risk_level === 'High').length;
    const studentCount = new Set(assessments.map((item) => item.student_id)).size;

    return (
        <div className="risk-page">
            <div className="risk-heading">
                <div>
                    <span className="eyebrow">SPRINT 1 · MANUAL ASSESSMENT</span>
                    <h1>Student risk assessment</h1>
                    <p>Review at-risk modules from the manually entered student data.</p>
                </div>
                <button className="refresh-button" onClick={loadAssessments} disabled={loading}>
                    <RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh
                </button>
            </div>

            <div className="summary-grid">
                <div className="summary-card"><span className="summary-icon red"><AlertTriangle size={19} /></span><div><span className="summary-label">At-risk modules</span><strong>{loading ? '—' : assessments.length}</strong></div></div>
                <div className="summary-card"><span className="summary-icon amber"><BookOpen size={19} /></span><div><span className="summary-label">High-risk modules</span><strong>{loading ? '—' : highRiskCount}</strong></div></div>
                <div className="summary-card"><span className="summary-icon green"><Users size={19} /></span><div><span className="summary-label">Students to follow up</span><strong>{loading ? '—' : studentCount}</strong></div></div>
            </div>

            <section className="assessment-panel">
                <div className="panel-heading">
                    <div><h2>Modules requiring attention</h2><p>Each row represents one student enrolled in one module.</p></div>
                    <label className="search-box"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search student or module" /></label>
                </div>
                {error ? <div className="notice error-notice"><strong>Assessment unavailable</strong><span>{error}</span><small>Confirm the training and manual input CSV files are in python/data, then restart the Python service.</small></div> : loading ? <div className="table-message">Loading risk assessments…</div> : filtered.length === 0 ? <div className="table-message">{assessments.length === 0 ? 'No at-risk modules found. Add student/module rows to python/data/manual_risk_inputs.csv and refresh.' : 'No results match your search.'}</div> : (
                    <div className="table-wrap"><table><thead><tr><th>Student</th><th>Module</th><th>Risk</th><th>Quiz accuracy</th><th>Engagement</th><th>Previous GPA</th><th>Difficulty</th></tr></thead><tbody>
                        {filtered.map((item, index) => <tr key={`${item.student_id}-${item.module_id}-${index}`}>
                            <td><strong>{item.student_name}</strong><span className="secondary">{item.student_id}</span></td>
                            <td><strong>{item.module_name}</strong><span className="secondary">{item.module_id}</span></td>
                            <td><span className={`risk-badge ${item.risk_level.toLowerCase()}`}><i />{item.risk_level} risk</span></td>
                            <td>{item.quiz_accuracy ?? '—'}%</td><td>{item.engagement_score ?? '—'}%</td><td>{item.previous_gpa ?? '—'}</td><td>{item.contextual_difficulty_level}</td>
                        </tr>)}
                    </tbody></table></div>
                )}
                <div className="data-note">Predictions use manually entered module data and the supplied learning outcome dataset. LMS results are not connected in this sprint.</div>
            </section>

            <style>{`
                .risk-page{max-width:1400px;margin:0 auto;padding:8px 0 30px;color:#202b36}.risk-heading{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:26px}.eyebrow{font-size:11px;letter-spacing:1.2px;font-weight:700;color:#328767}.risk-heading h1{font-size:28px;margin:8px 0;color:#213238}.risk-heading p,.panel-heading p{margin:0;color:#71808a;font-size:14px}.refresh-button{display:flex;align-items:center;gap:8px;border:1px solid #dce5e3;background:white;border-radius:10px;padding:10px 14px;color:#2d5550;font-weight:600;cursor:pointer}.refresh-button:disabled{opacity:.65}.summary-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:22px}.summary-card{display:flex;align-items:center;gap:14px;background:white;border:1px solid #edf0f1;border-radius:15px;padding:19px 20px;box-shadow:0 3px 14px rgba(33,50,56,.035)}.summary-card strong{display:block;margin-top:4px;font-size:25px;color:#26363c}.summary-label{font-size:13px;color:#74818a}.summary-icon{width:42px;height:42px;border-radius:12px;display:grid;place-items:center}.summary-icon.red{background:#fff0ed;color:#d85b49}.summary-icon.amber{background:#fff7e6;color:#c8891e}.summary-icon.green{background:#eaf7ef;color:#329064}.assessment-panel{background:#fff;border:1px solid #edf0f1;border-radius:16px;box-shadow:0 3px 14px rgba(33,50,56,.035);overflow:hidden}.panel-heading{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:22px 22px 18px}.panel-heading h2{font-size:17px;margin:0 0 6px;color:#293b40}.panel-heading p{font-size:13px}.search-box{display:flex;align-items:center;gap:8px;background:#f7f9f9;border:1px solid #e9eeee;border-radius:9px;padding:0 11px;color:#7a898b;min-width:240px}.search-box input{border:0;background:transparent;padding:10px 0;outline:none;color:#26363c;font:inherit;min-width:0;width:100%}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;text-align:left;white-space:nowrap}th{font-size:11px;text-transform:uppercase;letter-spacing:.55px;color:#75848a;background:#f8faf9;padding:12px 16px;font-weight:700}td{padding:15px 16px;border-top:1px solid #edf0f1;font-size:13px;color:#46565b}td strong{display:block;color:#293a40;font-weight:600}.secondary{display:block;font-size:11px;color:#8a969a;margin-top:4px}.risk-badge{display:inline-flex;align-items:center;gap:6px;border-radius:20px;padding:6px 9px;font-size:11px;font-weight:700}.risk-badge i{width:6px;height:6px;border-radius:50%;background:currentColor}.risk-badge.high{color:#bd493b;background:#fff0ed}.risk-badge.medium{color:#a97513;background:#fff6e3}.table-message{padding:48px 20px;text-align:center;color:#71808a;font-size:14px}.notice{margin:20px;padding:16px;border-radius:10px;display:grid;gap:6px;font-size:13px}.notice.error-notice{background:#fff5f3;color:#9d4439}.notice small{color:#7c6662}.data-note{padding:14px 20px;border-top:1px solid #edf0f1;color:#829096;font-size:11px}.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
                @media(max-width:760px){.risk-heading{align-items:flex-start}.risk-heading h1{font-size:23px}.summary-grid{grid-template-columns:1fr;gap:10px}.panel-heading{align-items:stretch;flex-direction:column}.search-box{min-width:0}.risk-heading p{max-width:420px}}
            `}</style>
        </div>
    );
};

export default RiskAssessment;
