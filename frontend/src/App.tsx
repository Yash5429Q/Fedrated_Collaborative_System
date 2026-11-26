import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { RouterProvider } from 'react-router-dom'
import { ShieldCheck, Lock, KeyRound, Eye, EyeOff, ArrowRight, LoaderCircle, AlertTriangle, Clock, Network, Activity } from 'lucide-react'
import { router } from './router'
import { apiClient, ApiError, clearAccessToken, setAccessToken, setAccessRole, type AccessRole } from './lib/apiClient'

export default function App() {
  const [ready, setReady] = useState(false)
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const denied = () => { setReady(false); setToken(''); setVisible(false); setError('Access expired, revoked or invalid. Enter a valid credential.') }
    const signOut = () => { clearAccessToken(); setReady(false); setToken(''); setVisible(false); setError('') }
    window.addEventListener('cyber20-sign-out', signOut)
    window.addEventListener('cyber20-access-denied', denied)
    return () => { window.removeEventListener('cyber20-access-denied', denied); window.removeEventListener('cyber20-sign-out', signOut) }
  }, [])

  async function signIn(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (busy || !token.trim()) return
    setBusy(true); setError(''); setVisible(false); setAccessToken(token)
    try {
      const session = await apiClient.get<{role: AccessRole}>('/access/session')
      if (session.role !== 'operator' && session.role !== 'viewer') throw new Error('Invalid session role')
      setAccessRole(session.role)
      setToken(''); setReady(true)
    } catch (err) {
      clearAccessToken()
      if (err instanceof ApiError && err.status === 401) {
        setError('Access expired, revoked or invalid. Request a valid credential from your administrator.')
      } else if (err instanceof ApiError && (err.status === 0 || err.status >= 500)) {
        setError('The server is temporarily unavailable. It may be starting up. Please try again shortly.')
      } else {
        setError('Unable to sign in. Verify your credential or contact your administrator.')
      }
    } finally { setBusy(false) }
  }

  if (ready) return <RouterProvider router={router} />

  return (
    <main className="secure-access">
      <div className="secure-shell">
        <section className="secure-intro" aria-labelledby="project-title">
          <div className="secure-brand"><span className="secure-logo"><ShieldCheck size={28} aria-hidden="true" /></span><span>CYBER-20<small>SECURITY RESEARCH PLATFORM</small></span></div>
          <div className="secure-intro-copy">
            <span className="secure-eyebrow"><span className="secure-dot" /> FEDERATED LEARNING · ACADEMIC DEMO</span>
            <h1 id="project-title">Collaborative intelligence.<br /><span>Stronger threat detection.</span></h1>
            <p>Explore how organisations can learn together using federated machine learning, without combining their raw training partitions.</p>
          </div>
          <div className="secure-features">
            <div><Network aria-hidden="true" /><span><strong>Federated learning</strong><small>Three simulated organisations</small></span></div>
            <div><Activity aria-hidden="true" /><span><strong>Threat classification</strong><small>Five network flow classes</small></span></div>
            <div><Lock aria-hidden="true" /><span><strong>Controlled access</strong><small>Role-based, expiring credentials</small></span></div>
          </div>
          <p className="secure-university">KL University <span>·</span> B.Tech Capstone Project</p>
        </section>
        <section className="secure-panel" aria-labelledby="signin-title">
          <div className="secure-access-tag"><Lock size={13} aria-hidden="true" /> AUTHORISED PERSONNEL ONLY</div>
          <h2 id="signin-title">Welcome to CYBER-20</h2>
          <p className="secure-subtitle">Sign in using the temporary access token issued by your project administrator.</p>
          <form onSubmit={signIn} className="secure-form" aria-busy={busy}>
            <label htmlFor="access-token">Access token</label>
            <div className="secure-input-wrap">
              <KeyRound size={19} aria-hidden="true" />
              <input id="access-token" name="access-token" type={visible ? 'text' : 'password'} autoComplete="off" autoCapitalize="none" spellCheck={false} required disabled={busy} value={token} onChange={e => { setToken(e.target.value); setError('') }} placeholder="Enter your secure access token" aria-invalid={!!error} aria-describedby={error ? 'access-error' : undefined} />
              <button type="button" className="secure-eye" disabled={busy} onClick={() => setVisible(v => !v)} aria-label={visible ? 'Hide access token' : 'Show access token'}>{visible ? <EyeOff size={19} /> : <Eye size={19} />}</button>
            </div>
            {error && <div id="access-error" className="secure-error" role="alert"><AlertTriangle size={18} aria-hidden="true" /><span>{error}</span></div>}
            <button type="submit" className="secure-submit" disabled={busy || !token.trim()}>{busy ? <><LoaderCircle className="secure-spinner" size={19} aria-hidden="true" /> Verifying access…</> : <>Secure Sign In <ArrowRight size={19} aria-hidden="true" /></>}</button>
            {busy && <p className="secure-wait" role="status">Connecting to the server. Cloud startup may take longer after inactivity.</p>}
          </form>
          <div className="secure-role-heading">ACCESS LEVELS</div>
          <div className="secure-roles">
            <div><ShieldCheck size={21} aria-hidden="true" /><strong>Operator</strong><small>View dashboards, classify flows and record prediction alerts.</small></div>
            <div><Eye size={21} aria-hidden="true" /><strong>Viewer</strong><small>Read-only monitoring and performance dashboards.</small></div>
          </div>
          <div className="secure-note"><Clock size={17} aria-hidden="true" /><p>Credentials expire automatically. Need access? Contact your project administrator. Public registration is disabled.</p></div>
        </section>
      </div>
      <footer className="secure-footer">CYBER-20 <span>·</span> Federated Collaborative Threat Detection <span>·</span> Academic prototype</footer>
    </main>
  )
}
