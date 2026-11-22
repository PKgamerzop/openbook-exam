import { useEffect, useState } from 'react'
import { Lecturer } from '../features/authoring/Lecturer'
import { Student } from '../features/exam/Student'
import { Diagnostics } from './App'
import { navigate } from './route'
import { api, useAction } from './api'

type User = { id: number; role: 'lecturer' | 'student'; username: string }
export function Portal() {
  const [user, setUser] = useState<User | null>()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { run, busy, error } = useAction()
  useEffect(() => {
    let live = true
    const expire = () => setUser(null)
    window.addEventListener('openbook-session-expired', expire)
    api<User>('/me')
      .then((u) => live && setUser(u))
      .catch(() => live && setUser(null))
    return () => {
      live = false
      window.removeEventListener('openbook-session-expired', expire)
    }
  }, [])
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
              OpenBook
            </a>
            <span>
              {user.username} · {user.role}
            </span>
            <button
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await api('/logout', 'POST')
                  setUser(null)
                  navigate('/')
                })
              }
            >
              Sign out
            </button>
          </header>
          {user.role === 'lecturer' ? <Lecturer /> : <Student />}
        </>
      ) : (
        <section className="sign-in">
          <h1>OpenBook</h1>
          <p className="description">Computer-based open-book examinations</p>
          <h2>Sign in</h2>
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
            <button disabled={busy}>Sign in</button>
          </form>
          <Diagnostics />
        </section>
      )}
      {error && <p role="alert">{error}</p>}
    </>
  )
}
