const API = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function jsonFetch(path, opts={}){
  const res = await fetch(`${API}${path}`, { headers: { "content-type":"application/json", ...(opts.headers||{}) }, ...opts });
  return res.json();
}
export async function formFetch(path, form){
  const res = await fetch(`${API}${path}`, { method:"POST", body:form });
  return res.json();
}