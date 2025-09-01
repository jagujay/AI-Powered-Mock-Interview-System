from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List
import uuid, os, json, io, subprocess, tempfile, textwrap
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

def bow_vector(text: str) -> Counter:
    tokens = [t.lower() for t in TOKEN_RE.findall(text or "")]
    return Counter(tokens)

def cosine_bow(a: Counter, b: Counter) -> float:
    # cosine between sparse Counters
    if not a or not b:
        return 0.0
    # dot product
    dot = sum(a[t] * b.get(t, 0) for t in a)
    # norms
    na = math.sqrt(sum(v*v for v in a.values()))
    nb = math.sqrt(sum(v*v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

def cosine_similarity_np(a, b):
    # a, b are 2D arrays from MODEL.encode([text]) => shape (1, D)
    num = float(np.dot(a, b.T))        # dot of (1,D)·(D,1) -> scalar
    den = float(np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)
    return num / den

app = FastAPI(title="AIMI API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; restrict in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- In-memory "DB" --------------------
USERS: Dict[str, Dict] = {}         # {user_id: {name,email,role}}
PROFILES: Dict[str, Dict] = {}      # {user_id: {...profile...}}
RESUMES: Dict[str, Dict] = {}       # {resume_id: {"text": "..."}}
JDS: Dict[str, Dict] = {}           # {jd_id: {"text": "..."}}
SESSIONS: Dict[str, Dict] = {}      # {session_id: {...}}
PROCTOR: Dict[str, List[Dict]] = {} # {session_id: [events]}

# Load models (small, fast)

SKILL_KEYWORDS = {
    "python": ["python","pandas","numpy","fastapi"],
    "sql": ["sql","postgres","mysql","sqlite"],
    "react": ["react","next.js","nextjs","typescript"],
    "system design": ["scalability","microservices","load balancer","cqrs","event-driven"],
    "kubernetes": ["kubernetes","k8s","helm"]
}

# -------------------- Schemas --------------------
class AuthIn(BaseModel):
    token: str  # pretend Firebase token

class AuthOut(BaseModel):
    jwt: str
    user: Dict

class ProfileIn(BaseModel):
    name: str = "Candidate"
    email: str = "user@example.com"
    links: List[str] = []

class NewSessionIn(BaseModel):
    type: str = Field(..., pattern="^(tech|hr)$")

class SessionOut(BaseModel):
    session_id: str

class MatchIn(BaseModel):
    resume_id: str
    jd_id: str

class SkillScore(BaseModel):
    name: str
    level: str  # "low" | "medium" | "high"

class MatchResult(BaseModel):
    score: float
    skills: List[SkillScore]
    gaps: List[str]

class MCQQuestion(BaseModel):
    id: str
    question: str
    options: List[str]
    index: int
    total: int

class MCQSubmitIn(BaseModel):
    session_id: str
    question_id: str
    selected_index: int

class MCQSubmitOut(BaseModel):
    correct: bool
    score_delta: int
    total_score: int
    next_available: bool

class HRAskOut(BaseModel):
    question: str

class HRIngestOut(BaseModel):
    transcript: str
    metrics: Dict

class ProctorEventIn(BaseModel):
    session_id: str
    type: str   # tab_blur|tab_focus|webcam_on|webcam_off
    meta: Dict = {}

class FeedbackOut(BaseModel):
    summary: str
    scores: Dict

# -------------------- Helpers --------------------
def _embed(text: str):
    return MODEL.encode([text])

def _skill_levels(resume_text: str, jd_text: str) -> List[SkillScore]:
    rt = resume_text.lower()
    jt = jd_text.lower()
    results = []
    for skill, kws in SKILL_KEYWORDS.items():
        if not any(k in jt for k in kws):
            continue
        hits = sum(1 for k in kws if k in rt)
        level = "high" if hits >= 2 else "medium" if hits == 1 else "low"
        results.append(SkillScore(name=skill.title(), level=level))
    return results

# -------------------- Health --------------------
@app.get("/v1/health")
def health():
    return {"status": "ok"}

# -------------------- Auth & Profiles --------------------
@app.post("/v1/auth/exchange", response_model=AuthOut)
def auth_exchange(body: AuthIn):
    # mock validation -> user
    user_id = "u_" + body.token[-6:] if body.token else "u_demo"
    USERS[user_id] = USERS.get(user_id, {"id": user_id, "role": "user"})
    return {"jwt": "demo.jwt."+user_id, "user": USERS[user_id]}

@app.post("/v1/profile")
def upsert_profile(user_id: str, body: ProfileIn):
    PROFILES[user_id] = body.model_dump()
    return {"ok": True, "profile": PROFILES[user_id]}

# -------------------- Resume & JD --------------------
@app.post("/v1/resumes")
async def create_resume(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="ignore")
    rid = f"res_{uuid.uuid4().hex[:8]}"
    RESUMES[rid] = {"text": content or f"[binary resume {file.filename}]"}
    return {"resume_id": rid}

@app.post("/v1/jds")
async def create_jd(jd: Dict):
    text = (jd or {}).get("jd_text", "")
    jid = f"jd_{uuid.uuid4().hex[:8]}"
    JDS[jid] = {"text": text}
    return {"jd_id": jid}

@app.post("/v1/match", response_model=MatchResult)
async def match(body: MatchIn):
    r = RESUMES.get(body.resume_id)
    j = JDS.get(body.jd_id)
    if not r or not j:
        return {"score": 0.0, "skills": [], "gaps": ["Invalid resume_id or jd_id"]}

    r_vec = bow_vector(r["text"])
    j_vec = bow_vector(j["text"])
    score = cosine_bow(r_vec, j_vec)

    skills = _skill_levels(r["text"], j["text"])  # keep your simple keyword heuristic
    gaps = [s.name for s in skills if s.level == "low"]
    return {"score": round(float(score), 2), "skills": skills, "gaps": gaps}

# -------------------- Question Generation (stub) --------------------
@app.post("/v1/questions/generate")
def generate_questions(jd_id: str):
    # simple filter from bank by keywords; later replace with LLM
    bank_path = os.path.join(os.path.dirname(__file__), "data", "mcq_bank.json")
    bank = json.load(open(bank_path, "r", encoding="utf-8"))
    jd_text = JDS.get(jd_id, {}).get("text", "").lower()
    picked = []
    for q in bank:
        if any(k in jd_text for k in ["python","sql","react","data","backend"]):
            picked.append(q)
    return {"mcqs": picked[:5], "coding": [{"id":"sum_two","title":"Sum Two Numbers"}]}

# -------------------- Technical Round (MCQ + Coding) --------------------
# MCQ state
BANK_PATH = os.path.join(os.path.dirname(__file__), "data", "mcq_bank.json")
MCQ_BANK = json.load(open(BANK_PATH, "r", encoding="utf-8"))

@app.post("/v1/sessions", response_model=SessionOut)
def create_session(body: NewSessionIn):
    sid = f"sess_{uuid.uuid4().hex[:8]}"
    SESSIONS[sid] = {"type": body.type, "cursor": 0, "answers": [], "score": 0}
    return {"session_id": sid}

@app.post("/v1/mcq/next", response_model=MCQQuestion)
def mcq_next(session_id: str):
    s = SESSIONS.get(session_id)
    if not s:
        raise HTTPException(400, "Invalid session_id")
    cur = s["cursor"]
    if cur >= len(MCQ_BANK):
        raise HTTPException(404, "No more questions")
    q = MCQ_BANK[cur]
    return {"id": q["id"], "question": q["question"], "options": q["options"], "index": cur, "total": len(MCQ_BANK)}

@app.post("/v1/mcq/submit", response_model=MCQSubmitOut)
def mcq_submit(body: MCQSubmitIn):
    s = SESSIONS.get(body.session_id)
    if not s: raise HTTPException(400, "Invalid session_id")
    cur = s["cursor"]
    if cur >= len(MCQ_BANK): raise HTTPException(404, "No more questions")
    q = MCQ_BANK[cur]
    is_correct = (body.selected_index == q["answer_index"])
    delta = 1 if is_correct else 0
    s["score"] += delta
    s["answers"].append({"id": q["id"], "selected": body.selected_index, "correct": is_correct})
    s["cursor"] += 1
    return {"correct": is_correct, "score_delta": delta, "total_score": s["score"], "next_available": s["cursor"] < len(MCQ_BANK)}

# Coding (dev-only, Python)
PROB_PATH = os.path.join(os.path.dirname(__file__), "data", "coding_problem.json")
PROB = json.load(open(PROB_PATH, "r", encoding="utf-8"))
SANDBOX_TEMPLATE = """
{user_code}
if _name_ == "_main_":
    import json, sys
    tests = json.loads(sys.stdin.read())
    outs = []
    for t in tests:
        a, b = t["input"]
        try:
            got = solve(a, b)
            outs.append({"ok": got == t["output"], "got": got, "want": t["output"]})
        except Exception as e:
            outs.append({"ok": False, "error": str(e)})
    print(json.dumps(outs))
"""

class CodeRunIn(BaseModel):
    problem_id: str
    lang: str = Field("python", pattern="^python$")
    code: str

class CodeRunOut(BaseModel):
    passed: int
    total: int
    results: List[Dict]
    error: str | None = None

@app.post("/v1/code/run", response_model=CodeRunOut)
def code_run(body: CodeRunIn):
    if body.problem_id != PROB["id"]:
        raise HTTPException(404, "Unknown problem")
    if body.lang != "python":
        raise HTTPException(400, "Only python supported in dev mode")
    code = textwrap.dedent(SANDBOX_TEMPLATE.format(user_code=body.code))
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write(code); tmp_path = tf.name
    try:
        proc = subprocess.run(["python", tmp_path], input=json.dumps(PROB["tests"]).encode("utf-8"),
                              capture_output=True, timeout=2)
        if proc.returncode != 0:
            return {"passed": 0, "total": len(PROB["tests"]), "results": [], "error": proc.stderr.decode()}
        outs = json.loads(proc.stdout.decode())
        passed = sum(1 for o in outs if o.get("ok"))
        return {"passed": passed, "total": len(PROB["tests"]), "results": outs, "error": None}
    except subprocess.TimeoutExpired:
        return {"passed": 0, "total": len(PROB["tests"]), "results": [], "error": "Timeout"}

# -------------------- HR Round (Voice) --------------------
HR_QUESTIONS = [
    "Tell me about a time you handled a conflict.",
    "Describe your most challenging project.",
    "Why do you want this role?",
]

@app.post("/v1/hr/ask", response_model=HRAskOut)
def hr_ask(session_id: str):
    if session_id not in SESSIONS: raise HTTPException(400, "Invalid session_id")
    idx = len([a for a in SESSIONS[session_id].get("hr", [])]) % len(HR_QUESTIONS)
    return {"question": HR_QUESTIONS[idx]}

@app.post("/v1/hr/ingest", response_model=HRIngestOut)
async def hr_ingest(session_id: str, audio: UploadFile = File(...), transcript: str | None = None):
    if session_id not in SESSIONS: raise HTTPException(400, "Invalid session_id")
    # (No STT yet) use provided transcript or a placeholder
    tx = transcript or "[audio received]"
    words = len(tx.split())
    metrics = {
        "words_per_min_approx": min(180, max(60, words)),  # toy metric
        "filler_ratio_approx": 0.05,                       # placeholder
        "sentiment_approx": "neutral"
    }
    SESSIONS[session_id].setdefault("hr", []).append({"transcript": tx, "metrics": metrics})
    return {"transcript": tx, "metrics": metrics}

# -------------------- Proctoring --------------------
@app.post("/v1/proctor/events")
def proctor_event(body: ProctorEventIn):
    PROCTOR.setdefault(body.session_id, []).append({"type": body.type, "meta": body.meta})
    return {"ok": True}

@app.get("/v1/proctor/flags")
def proctor_flags(session_id: str):
    events = PROCTOR.get(session_id, [])
    hard = any(e["type"] == "webcam_off" for e in events)
    soft = sum(1 for e in events if e["type"] == "tab_blur")
    return {"events": events, "hard_flag": hard, "soft_flag_count": soft}

# -------------------- Feedback --------------------
@app.post("/v1/feedback/finalize", response_model=FeedbackOut)
def feedback_finalize(session_id: str):
    s = SESSIONS.get(session_id, {})
    mcq_score = s.get("score", 0)
    hr_turns = s.get("hr", [])
    hr_score = 1 if hr_turns else 0
    summary = f"MCQ score={mcq_score}; HR turns={len(hr_turns)}."
    return {"summary": summary, "scores": {"mcq": mcq_score, "hr": hr_score}}