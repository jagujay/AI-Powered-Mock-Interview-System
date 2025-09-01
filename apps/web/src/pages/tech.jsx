import { useEffect, useState } from "react"
import { jsonFetch } from "../lib/api"
import { initProctor } from "../lib/proctor"

export default function Tech(){
  const [sessionId, setSessionId] = useState("")
  const [q, setQ] = useState(null)
  const [code, setCode] = useState("def solve(a,b):\n    return a+b")
  const [result, setResult] = useState(null)
  const [cleanup, setCleanup] = useState(()=>()=>{})

  useEffect(()=>()=>cleanup(),[cleanup])

  const start = async () => {
    const s = await jsonFetch("/v1/sessions", { method:"POST", body: JSON.stringify({ type:"tech" })})
    setSessionId(s.session_id)
    setCleanup(()=>initProctor(s.session_id))
  }
  const nextQ = async () => setQ(await jsonFetch(`/v1/mcq/next?session_id=${sessionId}`))
  const submit = async (i) => {
    const r = await jsonFetch("/v1/mcq/submit", { method:"POST", body: JSON.stringify({ session_id: sessionId, question_id: q.id, selected_index:i })})
    setResult(r); if (r.next_available) nextQ(); else setQ(null)
  }
  const runCode = async () => {
    const r = await jsonFetch("/v1/code/run", { method:"POST", body: JSON.stringify({ problem_id:"sum_two", lang:"python", code }) })
    setResult(r)
  }

  return (
    <div style={{display:"grid", gap:12, padding:16}}>
      <button className="button" onClick={start} disabled={!!sessionId}>Start Tech Session</button>
      {sessionId && !q && <button className="button" onClick={nextQ}>Next MCQ</button>}
      {q && (
        <div className="card">
          <b>Q{q.index+1}/{q.total}:</b> {q.question}
          <div style={{display:"grid", gap:6, marginTop:8}}>
            {q.options.map((opt,i)=>(<button key={i} className="button" onClick={()=>submit(i)}>{opt}</button>))}
          </div>
        </div>
      )}
      <div className="card">
        <h3>Coding</h3>
        <p>Problem: Sum Two Numbers (implement <code>solve(a,b)</code>)</p>
        <textarea className="input" rows={8} value={code} onChange={e=>setCode(e.target.value)} />
        <button className="button" onClick={runCode} style={{marginTop:8}}>Run Code</button>
      </div>
      {result && <pre className="card">{JSON.stringify(result,null,2)}</pre>}
    </div>
  )
}