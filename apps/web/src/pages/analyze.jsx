import { useState } from "react"
import { jsonFetch, formFetch } from "../lib/api"

export default function Analyze(){
  const [jd, setJd] = useState("Backend developer: Python + SQL")
  const [resumeFile, setResumeFile] = useState(null)
  const [match, setMatch] = useState(null)

  const run = async () => {
    const jdRes = await jsonFetch("/v1/jds", { method:"POST", body: JSON.stringify({ jd_text: jd })})
    const form = new FormData(); form.append("file", resumeFile || new Blob(["python, sql"], {type:"text/plain"}), "resume.txt")
    const upRes = await formFetch("/v1/resumes", form)
    const m = await jsonFetch("/v1/match", { method:"POST", body: JSON.stringify({ jd_id: jdRes.jd_id, resume_id: upRes.resume_id })})
    setMatch(m)
  }

  return (
    <div className="card" style={{margin:16}}>
      <h2>Resume–JD Analysis</h2>
      <textarea className="input" rows={5} value={jd} onChange={e=>setJd(e.target.value)} />
      <div style={{marginTop:8}}>
        <input type="file" onChange={e=>setResumeFile(e.target.files?.[0]||null)} />
      </div>
      <button className="button" onClick={run} style={{marginTop:8}}>Run Match</button>
      {match && <pre style={{marginTop:12}}>{JSON.stringify(match,null,2)}</pre>}
    </div>
  )
}