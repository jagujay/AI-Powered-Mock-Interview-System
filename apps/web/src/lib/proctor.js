// Basic proctoring: tab visibility + webcam permission signal
export function initProctor(sessionId, apiBase){
  const API = apiBase || (import.meta.env.VITE_API_BASE || "http://localhost:8000");
  const send = (type, meta={}) =>
    fetch(`${API}/v1/proctor/events`, { method:"POST", headers:{ "content-type":"application/json" }, body: JSON.stringify({ session_id: sessionId, type, meta })});

  const vis = () => document.visibilityState === "hidden" ? send("tab_blur") : send("tab_focus");
  document.addEventListener("visibilitychange", vis);

  // Ask webcam permission once; we only flag on/off (no video processing here)
  navigator.mediaDevices?.getUserMedia?.({ video:true })
    .then(stream => { send("webcam_on"); stream.getTracks().forEach(t=>t.stop()); })
    .catch(()=> send("webcam_off"));

  return () => document.removeEventListener("visibilitychange", vis);
}