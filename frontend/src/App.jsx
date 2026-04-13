import React, { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, useParams } from 'react-router-dom';
import { auth, tickets, incidents, comments, attachments, assets, reports, webhooks, audit, users, organizations, tokens, enrichment } from './services/api';

const AuthContext = createContext(null);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    auth.csrf()
      .catch(() => null)
      .then(() => auth.me())
      .then((r) => {
        if (active) setUser(r.data);
      })
      .catch(() => {
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const login = async (creds) => {
    await auth.csrf();
    const r = await auth.login(creds);
    setUser(r.data.user);
    return r.data;
  };

  const logout = async () => {
    await auth.csrf();
    await auth.logout();
    setUser(null);
  };

  if (loading) return <div className="loading"><div className="spinner"></div></div>;
  return <AuthContext.Provider value={{ user, login, logout, setUser }}>{children}</AuthContext.Provider>;
}

const useAuth = () => useContext(AuthContext);

function Toast({ message, type, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, [onClose]);
  return <div className={`toast toast-${type}`}>{message}</div>;
}

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed');
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-title">VulnOps</div>
        <div className="login-subtitle">Service Desk - Sign In</div>
        {error && <div style={{ background: 'var(--danger-light)', color: 'var(--danger)', padding: '8px 12px', borderRadius: 6, marginBottom: 16, fontSize: 13 }}>{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <input className="form-input" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} required />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input className="form-input" type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} required />
          </div>
          <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>{loading ? 'Signing in...' : 'Sign In'}</button>
        </form>
      </div>
    </div>
  );
}

function Sidebar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const nav = (path) => navigate(path);
  const isActive = (path) => location.pathname.startsWith(path) ? 'nav-item active' : 'nav-item';

  return (
    <div className="sidebar">
      <div className="sidebar-logo"><span>●</span> VulnOps</div>
      <div className="sidebar-nav">
        <div className="nav-section">Main</div>
        <button className={isActive('/dashboard')} onClick={() => nav('/dashboard')}>📊 Dashboard</button>
        <button className={isActive('/tickets')} onClick={() => nav('/tickets')}>🎫 Tickets</button>
        <button className={isActive('/incidents')} onClick={() => nav('/incidents')}>🚨 Incidents</button>
        <button className={isActive('/assets')} onClick={() => nav('/assets')}>💻 Assets</button>
        <div className="nav-section">Operations</div>
        <button className={isActive('/reports')} onClick={() => nav('/reports')}>📋 Reports</button>
        <button className={isActive('/imports')} onClick={() => nav('/imports')}>📥 Import</button>
        <button className={isActive('/webhooks')} onClick={() => nav('/webhooks')}>🔗 Webhooks</button>
        <div className="nav-section">Admin</div>
        <button className={isActive('/users')} onClick={() => nav('/users')}>👥 Users</button>
        <button className={isActive('/org-admin')} onClick={() => nav('/org-admin')}>🏢 Organization</button>
        <button className={isActive('/sys-admin')} onClick={() => nav('/sys-admin')}>⚙️ System</button>
        <button className={isActive('/audit')} onClick={() => nav('/audit')}>📝 Audit Log</button>
      </div>
      <div className="sidebar-footer">
        <div style={{ fontWeight: 600, color: '#fff' }}>{user?.username}</div>
        <div>{user?.role} · {user?.organization_name || 'No org'}</div>
        <button className="nav-item" style={{ marginTop: 8, padding: '6px 0' }} onClick={logout}>🚪 Sign Out</button>
      </div>
    </div>
  );
}

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    Promise.all([tickets.list({ page_size: 5 }), incidents.list({ page_size: 5 }), assets.list({ page_size: 1 })])
      .then(([t, i, a]) => {
        setRecent(t.data.results || t.data || []);
        setStats({
          tickets: t.data.count || (t.data.results || t.data || []).length,
          incidents: i.data.count || (i.data.results || i.data || []).length,
          assets: a.data.count || (a.data.results || a.data || []).length,
        });
      }).catch(() => {});
  }, []);

  return (
    <>
      <div className="topbar"><div className="topbar-title">Dashboard</div></div>
      <div className="page-content">
        <div className="stats-grid">
          <div className="stat-card"><div className="stat-label">Open Tickets</div><div className="stat-value">{stats?.tickets || '—'}</div></div>
          <div className="stat-card"><div className="stat-label">Active Incidents</div><div className="stat-value">{stats?.incidents || '—'}</div></div>
          <div className="stat-card"><div className="stat-label">Managed Assets</div><div className="stat-value">{stats?.assets || '—'}</div></div>
          <div className="stat-card"><div className="stat-label">System Status</div><div className="stat-value" style={{ color: 'var(--success)' }}>Healthy</div></div>
        </div>
        <div className="card">
          <div className="card-title">Recent Tickets</div>
          <div className="table-container">
            <table>
              <thead><tr><th>Title</th><th>Status</th><th>Priority</th><th>Created</th></tr></thead>
              <tbody>
                {(Array.isArray(recent) ? recent : []).slice(0, 5).map(t => (
                  <tr key={t.id}><td><a href={`/tickets/${t.id}`}>{t.title}</a></td><td><span className={`badge badge-${t.status}`}>{t.status}</span></td><td><span className={`badge badge-${t.priority}`}>{t.priority}</span></td><td>{new Date(t.created_at).toLocaleDateString()}</td></tr>
                ))}
                {(!recent || recent.length === 0) && <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--gray-400)' }}>No tickets yet</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

function ListPage({ title, fetchFn, columns, createPath, detailPath }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    fetchFn().then(r => setData(r.data.results || r.data || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="topbar">
        <div className="topbar-title">{title}</div>
        <div className="topbar-actions">
          {createPath && <button className="btn btn-primary" onClick={() => navigate(createPath)}>+ Create</button>}
        </div>
      </div>
      <div className="page-content">
        {loading ? <div className="loading"><div className="spinner"></div></div> : (
          <div className="card">
            <div className="table-container">
              <table>
                <thead><tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead>
                <tbody>
                  {data.map(item => (
                    <tr key={item.id} style={{ cursor: detailPath ? 'pointer' : 'default' }} onClick={() => detailPath && navigate(detailPath(item))}>
                      {columns.map(c => <td key={c.key}>{c.render ? c.render(item) : item[c.key]}</td>)}
                    </tr>
                  ))}
                  {data.length === 0 && <tr><td colSpan={columns.length}><div className="empty-state"><h3>No items found</h3></div></td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function TicketsPage() {
  return <ListPage title="Tickets" fetchFn={() => tickets.list()} columns={[
    { key: 'title', label: 'Title' },
    { key: 'status', label: 'Status', render: t => <span className={`badge badge-${t.status}`}>{t.status}</span> },
    { key: 'priority', label: 'Priority', render: t => <span className={`badge badge-${t.priority}`}>{t.priority}</span> },
    { key: 'reporter_name', label: 'Reporter' },
    { key: 'created_at', label: 'Created', render: t => new Date(t.created_at).toLocaleDateString() },
  ]} createPath="/tickets/new" detailPath={t => `/tickets/${t.id}`} />;
}

function TicketDetail() {
  const { id } = useParams();
  const [ticket, setTicket] = useState(null);
  const [cmts, setCmts] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [toast, setToast] = useState(null);

  useEffect(() => {
    tickets.get(id).then(r => setTicket(r.data)).catch(() => {});
    comments.list({ ticket: id }).then(r => setCmts(r.data.results || r.data || [])).catch(() => {});
  }, [id]);

  const addComment = async () => {
    if (!newComment.trim()) return;
    try {
      await comments.create({ ticket: id, content: newComment });
      setNewComment('');
      comments.list({ ticket: id }).then(r => setCmts(r.data.results || r.data || []));
      setToast({ message: 'Comment added', type: 'success' });
    } catch { setToast({ message: 'Failed to add comment', type: 'error' }); }
  };

  if (!ticket) return <div className="loading"><div className="spinner"></div></div>;

  return (
    <>
      <div className="topbar"><div className="topbar-title">Ticket: {ticket.title}</div></div>
      <div className="page-content">
        <div className="card">
          <div className="detail-header">
            <div>
              <h2>{ticket.title}</h2>
              <div className="detail-meta">
                <div className="detail-meta-item">Status: <span className={`badge badge-${ticket.status}`}>{ticket.status}</span></div>
                <div className="detail-meta-item">Priority: <span className={`badge badge-${ticket.priority}`}>{ticket.priority}</span></div>
                <div className="detail-meta-item">Reporter: <strong>{ticket.reporter_name}</strong></div>
                <div className="detail-meta-item">Assignee: <strong>{ticket.assignee_name || 'Unassigned'}</strong></div>
              </div>
            </div>
          </div>
          <p style={{ lineHeight: 1.6 }}>{ticket.description}</p>
        </div>

        <div className="card">
          <div className="card-title">Comments ({cmts.length})</div>
          <div className="timeline">
            {cmts.map(c => (
              <div key={c.id} className="timeline-item">
                <span className="timeline-author">{c.author_name}</span>
                <span className="timeline-date">{new Date(c.created_at).toLocaleString()}</span>
                { }
                <div className="timeline-content" dangerouslySetInnerHTML={{ __html: c.content_html || c.content }} />
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16 }}>
            <textarea className="form-textarea" placeholder="Add a comment (supports markdown)..." value={newComment} onChange={e => setNewComment(e.target.value)} />
            <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={addComment}>Add Comment</button>
          </div>
        </div>
      </div>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </>
  );
}

function CreateTicket() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium', category: 'general' });
  const [toast, setToast] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await tickets.create(form);
      navigate(`/tickets/${r.data.id}`);
    } catch (err) {
      setToast({ message: err.response?.data?.detail || 'Failed to create ticket', type: 'error' });
    }
  };

  return (
    <>
      <div className="topbar"><div className="topbar-title">Create Ticket</div></div>
      <div className="page-content">
        <div className="card" style={{ maxWidth: 700 }}>
          <form onSubmit={handleSubmit}>
            <div className="form-group"><label className="form-label">Title</label><input className="form-input" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} required /></div>
            <div className="form-group"><label className="form-label">Description</label><textarea className="form-textarea" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} required /></div>
            <div style={{ display: 'flex', gap: 16 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Priority</label>
                <select className="form-select" value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}>
                  <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option>
                </select>
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Category</label>
                <input className="form-input" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} />
              </div>
            </div>
            <div className="modal-actions"><button className="btn" type="button" onClick={() => navigate('/tickets')}>Cancel</button><button className="btn btn-primary" type="submit">Create Ticket</button></div>
          </form>
        </div>
      </div>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </>
  );
}

function IncidentsPage() {
  return <ListPage title="Incidents" fetchFn={() => incidents.list()} columns={[
    { key: 'title', label: 'Title' },
    { key: 'severity', label: 'Severity', render: i => <span className={`badge badge-${i.severity}`}>{i.severity}</span> },
    { key: 'status', label: 'Status', render: i => <span className={`badge badge-${i.status}`}>{i.status}</span> },
    { key: 'reporter_name', label: 'Reporter' },
    { key: 'created_at', label: 'Created', render: i => new Date(i.created_at).toLocaleDateString() },
  ]} detailPath={i => `/incidents/${i.id}`} />;
}

function AssetsPage() {
  return <ListPage title="Assets" fetchFn={() => assets.list()} columns={[
    { key: 'name', label: 'Name' },
    { key: 'asset_tag', label: 'Tag' },
    { key: 'asset_type', label: 'Type' },
    { key: 'status', label: 'Status', render: a => <span className={`badge badge-${a.status}`}>{a.status}</span> },
    { key: 'location', label: 'Location' },
    { key: 'department', label: 'Department' },
  ]} />;
}

function ReportsPage() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    reports.list().then(r => setJobs(r.data.results || r.data || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const createReport = async () => {
    try {
      await reports.create({ name: `Report ${new Date().toISOString().slice(0, 10)}`, report_type: 'tickets', output_format: 'csv', parameters: {} });
      reports.list().then(r => setJobs(r.data.results || r.data || []));
      setToast({ message: 'Report generation started', type: 'success' });
    } catch { setToast({ message: 'Failed to create report', type: 'error' }); }
  };

  return (
    <>
      <div className="topbar"><div className="topbar-title">Reports</div><div className="topbar-actions"><button className="btn btn-primary" onClick={createReport}>+ Generate Report</button></div></div>
      <div className="page-content">
        <div className="card">
          {loading ? <div className="loading"><div className="spinner"></div></div> : (
            <table><thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Rows</th><th>Created</th></tr></thead>
              <tbody>
                {jobs.map(j => <tr key={j.id}><td>{j.name}</td><td>{j.report_type}</td><td><span className={`badge badge-${j.status}`}>{j.status}</span></td><td>{j.row_count}</td><td>{new Date(j.created_at).toLocaleString()}</td></tr>)}
                {jobs.length === 0 && <tr><td colSpan={5}><div className="empty-state"><h3>No reports generated yet</h3></div></td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </>
  );
}

function ImportsPage() {
  const [file, setFile] = useState(null);
  const [toast, setToast] = useState(null);

  const handleImport = async () => {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const r = await assets.importData(fd);
      setToast({ message: `Imported ${r.data.created} assets`, type: 'success' });
      setFile(null);
    } catch (err) {
      setToast({ message: err.response?.data?.error || 'Import failed', type: 'error' });
    }
  };

  return (
    <>
      <div className="topbar"><div className="topbar-title">Import Data</div></div>
      <div className="page-content">
        <div className="card" style={{ maxWidth: 600 }}>
          <div className="card-title">Import Assets</div>
          <p style={{ marginBottom: 16, color: 'var(--gray-500)', fontSize: 13 }}>Upload a file to import assets. Supported formats: CSV, JSON, YAML.</p>
          <div className="form-group">
            <input type="file" onChange={e => setFile(e.target.files[0])} accept=".csv,.json,.yaml,.yml" />
          </div>
          <button className="btn btn-primary" onClick={handleImport} disabled={!file}>Import</button>
        </div>
      </div>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </>
  );
}

function WebhooksPage() {
  const [hooks, setHooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    webhooks.list().then(r => setHooks(r.data.results || r.data || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const testWebhook = async (id) => {
    try {
      const r = await webhooks.test(id);
      setToast({ message: `Test sent! Status: ${r.data.status}`, type: 'success' });
    } catch { setToast({ message: 'Test delivery failed', type: 'error' }); }
  };

  return (
    <>
      <div className="topbar"><div className="topbar-title">Webhook Integrations</div></div>
      <div className="page-content">
        <div className="card">
          {loading ? <div className="loading"><div className="spinner"></div></div> : (
            <table><thead><tr><th>Name</th><th>URL</th><th>Events</th><th>Active</th><th>Actions</th></tr></thead>
              <tbody>
                {hooks.map(h => <tr key={h.id}><td>{h.name}</td><td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{h.url}</td><td>{(h.events || []).join(', ')}</td><td>{h.is_active ? '✅' : '❌'}</td><td><button className="btn btn-sm" onClick={() => testWebhook(h.id)}>Test</button></td></tr>)}
                {hooks.length === 0 && <tr><td colSpan={5}><div className="empty-state"><h3>No webhooks configured</h3></div></td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </>
  );
}

function UsersPage() {
  return <ListPage title="Users" fetchFn={() => users.list()} columns={[
    { key: 'username', label: 'Username' },
    { key: 'email', label: 'Email' },
    { key: 'role', label: 'Role', render: u => <span className="badge">{u.role}</span> },
    { key: 'is_active', label: 'Active', render: u => u.is_active ? '✅' : '❌' },
    { key: 'last_login', label: 'Last Login', render: u => u.last_login ? new Date(u.last_login).toLocaleString() : 'Never' },
  ]} />;
}

function OrgAdminPage() {
  const { user } = useAuth();
  const [org, setOrg] = useState(null);
  const [members, setMembers] = useState([]);

  useEffect(() => {
    if (user?.organization) {
      organizations.get(user.organization).then(r => setOrg(r.data)).catch(() => {});
      users.list({ organization: user.organization }).then(r => setMembers(r.data.results || r.data || [])).catch(() => {});
    }
  }, [user]);

  return (
    <>
      <div className="topbar"><div className="topbar-title">Organization Settings</div></div>
      <div className="page-content">
        <div className="card">
          <div className="card-title">Organization Details</div>
          {org ? (
            <div><p><strong>Name:</strong> {org.name}</p><p><strong>Slug:</strong> {org.slug}</p><p><strong>Plan:</strong> {org.plan}</p></div>
          ) : <p style={{ color: 'var(--gray-400)' }}>No organization assigned</p>}
        </div>
        <div className="card">
          <div className="card-title">Members ({members.length})</div>
          <table><thead><tr><th>Username</th><th>Role</th><th>Department</th></tr></thead>
            <tbody>{members.map(m => <tr key={m.id}><td>{m.username}</td><td>{m.role}</td><td>{m.department}</td></tr>)}</tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function SysAdminPage() {
  const [orgs, setOrgs] = useState([]);
  const [userCount, setUserCount] = useState(0);

  useEffect(() => {
    organizations.list().then(r => setOrgs(r.data.results || r.data || [])).catch(() => {});
    users.list().then(r => setUserCount(r.data.count || (r.data.results || r.data || []).length)).catch(() => {});
  }, []);

  return (
    <>
      <div className="topbar"><div className="topbar-title">System Administration</div></div>
      <div className="page-content">
        <div className="stats-grid">
          <div className="stat-card"><div className="stat-label">Total Organizations</div><div className="stat-value">{orgs.length}</div></div>
          <div className="stat-card"><div className="stat-label">Total Users</div><div className="stat-value">{userCount}</div></div>
        </div>
        <div className="card">
          <div className="card-title">Organizations</div>
          <table><thead><tr><th>Name</th><th>Slug</th><th>Plan</th><th>Active</th></tr></thead>
            <tbody>{orgs.map(o => <tr key={o.id}><td>{o.name}</td><td>{o.slug}</td><td>{o.plan}</td><td>{o.is_active ? '✅' : '❌'}</td></tr>)}</tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function AuditPage() {
  return <ListPage title="Audit Log" fetchFn={() => audit.list()} columns={[
    { key: 'action', label: 'Action', render: e => <span className="badge">{e.action}</span> },
    { key: 'resource_type', label: 'Resource' },
    { key: 'description', label: 'Description' },
    { key: 'username', label: 'User' },
    { key: 'ip_address', label: 'IP' },
    { key: 'created_at', label: 'Time', render: e => new Date(e.created_at).toLocaleString() },
  ]} />;
}

function PasswordResetPage() {
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPass, setNewPass] = useState('');
  const [msg, setMsg] = useState('');

  const requestReset = async (e) => {
    e.preventDefault();
    try {
      const r = await auth.resetRequest({ email });
      setMsg(r.data.debug_token ? `Token issued. Debug token: ${r.data.debug_token}` : 'If the account exists, a reset token has been issued.');
      setStep(2);
    } catch (err) { setMsg(err.response?.data?.error || 'Failed'); }
  };

  const confirmReset = async (e) => {
    e.preventDefault();
    try {
      await auth.resetConfirm({ email, token, new_password: newPass });
      setMsg('Password reset successful! You can now log in.');
    } catch (err) { setMsg(err.response?.data?.error || 'Failed'); }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-title">Password Reset</div>
        {msg && <div style={{ background: 'var(--primary-light)', padding: '8px 12px', borderRadius: 6, marginBottom: 16, fontSize: 13 }}>{msg}</div>}
        {step === 1 ? (
          <form onSubmit={requestReset}>
            <div className="form-group"><label className="form-label">Email</label><input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required /></div>
            <button className="btn btn-primary" style={{ width: '100%' }}>Request Reset Token</button>
          </form>
        ) : (
          <form onSubmit={confirmReset}>
            <div className="form-group"><label className="form-label">Reset Token</label><input className="form-input" value={token} onChange={e => setToken(e.target.value)} required /></div>
            <div className="form-group"><label className="form-label">New Password</label><input className="form-input" type="password" value={newPass} onChange={e => setNewPass(e.target.value)} required /></div>
            <button className="btn btn-primary" style={{ width: '100%' }}>Reset Password</button>
          </form>
        )}
        <div style={{ textAlign: 'center', marginTop: 16 }}><a href="/login">Back to Login</a></div>
      </div>
    </div>
  );
}

function AppLayout({ children }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">{children}</div>
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <AppLayout>{children}</AppLayout>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/password-reset" element={<PasswordResetPage />} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/tickets" element={<ProtectedRoute><TicketsPage /></ProtectedRoute>} />
          <Route path="/tickets/new" element={<ProtectedRoute><CreateTicket /></ProtectedRoute>} />
          <Route path="/tickets/:id" element={<ProtectedRoute><TicketDetail /></ProtectedRoute>} />
          <Route path="/incidents" element={<ProtectedRoute><IncidentsPage /></ProtectedRoute>} />
          <Route path="/assets" element={<ProtectedRoute><AssetsPage /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><ReportsPage /></ProtectedRoute>} />
          <Route path="/imports" element={<ProtectedRoute><ImportsPage /></ProtectedRoute>} />
          <Route path="/webhooks" element={<ProtectedRoute><WebhooksPage /></ProtectedRoute>} />
          <Route path="/users" element={<ProtectedRoute><UsersPage /></ProtectedRoute>} />
          <Route path="/org-admin" element={<ProtectedRoute><OrgAdminPage /></ProtectedRoute>} />
          <Route path="/sys-admin" element={<ProtectedRoute><SysAdminPage /></ProtectedRoute>} />
          <Route path="/audit" element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
