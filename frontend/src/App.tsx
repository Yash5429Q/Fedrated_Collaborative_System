import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import { apiClient, clearAccessToken, setAccessToken } from './lib/apiClient'

export default function App() {
  const [ready, setReady] = useState(false)
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    const denied = () => { setReady(false); setToken(''); setError('Access expired, revoked or invalid. Enter a valid credential.') }
    window.addEventListener('cyber20-access-denied', denied)
    return () => window.removeEventListener('cyber20-access-denied', denied)
  }, [])
  async function signIn(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setBusy(true); setError(''); setAccessToken(token)
    try {
      await apiClient.get('/predict/health')
      setToken(''); setReady(true)
    } catch (err) {
      clearAccessToken(); setError(err instanceof Error ? err.message : 'Access failed')
    } finally { setBusy(false) }
  }
  if (ready) return <><button type="button" style={{position:'fixed',right:16,bottom:16,zIndex:1000,padding:10,background:'#26364b',color:'white',borderRadius:8}} onClick={() => {clearAccessToken(); setReady(false); setToken(''); setError('')}}>Sign out</button><RouterProvider router={router} /></>
  return <main style={{minHeight:'100vh',display:'grid',placeItems:'center',background:'#101827',color:'white'}}>
    <form onSubmit={signIn} style={{width:'min(90vw, 420px)',padding:28,border:'1px solid #536175',borderRadius:12,display:'grid',gap:16}}>
      <h1 style={{fontSize:24,fontWeight:600}}>CYBER-20 — Secure access</h1>
      <p>Enter a temporary viewer or operator credential issued by the local administrator.</p>
      <label htmlFor="access-token">Access token</label>
      <input id="access-token" type="password" autoComplete="off" required value={token} onChange={e => setToken(e.target.value)} style={{padding:10,color:'#101827',background:'white',borderRadius:6}} />
      {error && <p role="alert" style={{color:'#fca5a5'}}>{error}</p>}
      <button type="submit" disabled={busy || !token.trim()} style={{padding:10,background:'#2563eb',borderRadius:6}}>{busy?'Checking…':'Sign in'}</button>
    </form>
  </main>
}
