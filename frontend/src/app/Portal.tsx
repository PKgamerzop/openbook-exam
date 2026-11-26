import { useEffect, useState } from 'react'
import { Lecturer } from '../features/authoring/Lecturer'
import { Student } from '../features/exam/Student'
import { Diagnostics } from './App'
import { navigate } from './route'
import { ApiError, api, useAction } from './api'
import { Icon } from './Icon'

type User = { id: number; role: 'lecturer' | 'student'; username: string }
export function Portal() {
  const [user, setUser] = useState<User | null>()
  const [sessionUnavailable, setSessionUnavailable] = useState(false)
  const [sessionCheck, setSessionCheck] = useState(0)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { run, busy, error } = useAction()
  useEffect(() => {
    let live = true
    const expire = () => setUser(null)
    window.addEventListener('openbook-session-expired', expire)
    api<User>('/me')
      .then((u) => live && setUser(u))
      .catch((failure: unknown) => {
        if (!live) return
        if (failure instanceof ApiError && failure.status === 401) setUser(null)
        else setSessionUnavailable(true)
      })
    return () => {
      live = false
      window.removeEventListener('openbook-session-expired', expire)
    }
  }, [sessionCheck])
  if (sessionUnavailable)
    return (
      <section className="sign-in">
        <h1>OpenBook</h1>
        <p role="alert">The examination service is temporarily unavailable.</p>
        <button
          onClick={() => {
            setSessionUnavailable(false)
            setSessionCheck((previous) => previous + 1)
          }}
        >
          Retry connection
        </button>
      </section>
    )
  if (user === undefined) return <p role="status">Checking session…</p>
  return (
    <>
      {user ? (
        <>
          <header className="session-bar">
            <a
              className="wordmark"
              href="/"
              onClick={(e) => {
                e.preventDefault()
                navigate('/')
              }}
            >
              <span className="brand-icon"><Icon name="book" /></span>
              OpenBook
            </a>
            <div className="session-identity">
              <span className="session-avatar" aria-hidden="true">{user.username.slice(0, 1).toUpperCase()}</span>
              <div><strong>{user.username}</strong><small>{user.role}</small></div>
            </div>
            <button
              className="button-secondary sign-out"
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await api('/logout', 'POST')
                  setUser(null)
                  navigate('/')
                })
              }
            >
              <Icon name="logout" /> Sign out
            </button>
          </header>
          {user.role === 'lecturer' ? <Lecturer /> : <Student />}
        </>
      ) : (
        <div className="sign-in-layout">
          <aside className="sign-in-brand">
            <div className="wordmark"><span className="brand-icon"><Icon name="book" /></span> OpenBook</div>
            <div className="sign-in-copy"><p>Examination portal</p><span>Computer-based open-book examinations</span></div>
            <Icon name="book" className="sign-in-illustration" />
          </aside>
          <section className="sign-in">
            <h1>Sign in</h1>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                void run(async () => {
                  const u = await api<User>('/login', 'POST', {
                    username,
                    password,
                  })
                  setPassword('')
                  setUser(u)
                })
              }}
            >
              <label>
                Username
                <input
                  required
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </label>
              <label>
                Password
                <input
                  required
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <button disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}<Icon name="right" /></button>
            </form>
            {error && <p role="alert">{error}</p>}
            <Diagnostics />
          </section>
        </div>
      )}
      {user && error && <p className="session-error" role="alert">{error}</p>}
    </>
  )
}
