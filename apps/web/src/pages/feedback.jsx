import { useState } from "react"
import { jsonFetch } from "../lib/api"

export default function Feedback(){
  const [sessionId, setSessionId] = useState("")
  const [report, setReport] = useState(null)
  const [proctor, setProctor] = useState(null)

  const finalize = async () => setReport(await jsonFetch(`/v1/feedback/finalize?session_id=${sessionId}`))
  const flags = async () => setProctor(await jsonFetch(`/v1/proctor/flags?session_id=${sessionId}`))

  return (
    <div className="card" style={{margin:16}}>
      <h2>Feedback & Proctoring</h2>
      <input className="input" placeholder="session id (tech or hr)" value={sessionId} onChange={e=>setSessionId(e.target.value)} />
      <div style={{display:"flex", gap:8, marginTop:8}}>
        <button className="button" onClick={finalize}>Finalize Feedback</button>
        <button className="button" onClick={flags}>View Proctor Flags</button>
      </div>
      {report && <pre style={{marginTop:12}}>{JSON.stringify(report,null,2)}</pre>}
      {proctor && <pre style={{marginTop:12}}>{JSON.stringify(proctor,null,2)}</pre>}
    </div>
  )
}