import { useState } from "react"
import { jsonFetch } from "../lib/api"

export default function Login(){
  const [token, setToken] = useState("")
  const [user, setUser] = useState(null)

  const login = async () => {
    const data = await jsonFetch("/v1/auth/exchange", { method:"POST", body: JSON.stringify({ token }) })
    setUser(data.user)
  }

  return (
    <div className="card" style={{margin:16}}>
      <h2>Login (Mock)</h2>
      <input className="input" placeholder="paste mock token" value={token} onChange={e=>setToken(e.target.value)}/>
      <button className="button" onClick={login} style={{marginTop:8}}>Login</button>
      {user && <pre style={{marginTop:12}}>{JSON.stringify(user,null,2)}</pre>}
    </div>
  )
}