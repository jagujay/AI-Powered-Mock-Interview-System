import { useEffect, useState } from "react"
import { jsonFetch } from "../lib/api"
import { initProctor } from "../lib/proctor"

export default function HR(){
  const [sessionId, setSessionId] = useState("")
  const [question, setQuestion] = useState("")
  const [transcript, setTranscript] = useState("")
  const [metrics, setMetrics] = useState(null)
  const [cleanup, setCleanup] = useState(()=>()=>{})

  useEffect(()=>()=>cleanup(),[cleanup])

  const start = async () => {
    const s = await jsonFetch("/v1/sessions", { method:"POST", body: JSON.stringify({ type:"hr" })})
    setSessionId(s.session_id)
    setCleanup(()=>initProctor(s.session_id))
  }
  const ask = async () => {
    const q = await jsonFetch(`/v1/hr/ask?session_id=${sessionId}`)
    setQuestion(q.question)
  }
  const submit = async () => {
    const blob = new Blob(["fakeaudio"], {type:"audio/webm"})
    const form = new FormData()
    form.append("audio", blob, "resp.webm")
    form.append("transcript", transcript || "My experience includes Python and SQL projects...")
    const res = await fetch((import.meta.env.VITE_API_BASE||"http://localhost:8000")+"/v1/hr/ingest?session_id="+sessionId, { method:"POST", body: form }).then(r=>r.json())
    setMetrics(res.metrics)
  }

  return (
    <div className="card" style={{margin:16}}>
      <h2>HR Round (Voice) — Dev Mock</h2>
      <button className="button" onClick={start} disabled={!!sessionId}>Start HR Session</button>
      {sessionId && <button className="button" onClick={ask} style={{marginLeft:8}}>Ask Question</button>}
      {question && <p style={{marginTop:8}}><b>Question:</b> {question}</p>}
      <textarea className="input" rows={4} placeholder="(Dev) Paste or type transcript here…" value={transcript} onChange={e=>setTranscript(e.target.value)} />
      <button className="button" onClick={submit} style={{marginTop:8}}>Submit Answer</button>
      {metrics && <pre style={{marginTop:12}}>{JSON.stringify(metrics,null,2)}</pre>}
    </div>
  )
}