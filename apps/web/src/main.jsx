import React from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter, Routes, Route, Link } from "react-router-dom"
import "./styles.css"
import App from "./app"
import Login from "./pages/login"
import Analyze from "./pages/analyze"
import Tech from "./pages/tech"
import HR from "./pages/HR"
import Feedback from "./pages/feedback"

createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <div className="nav">
      <Link to="/">Home</Link>
      <Link to="/analyze">Analyze</Link>
      <Link to="/tech">Tech</Link>
      <Link to="/hr">HR</Link>
      <Link to="/feedback">Feedback</Link>
    </div>
    <Routes>
      <Route path="/" element={<App/>} />
      <Route path="/login" element={<Login/>} />
      <Route path="/analyze" element={<Analyze/>} />
      <Route path="/tech" element={<Tech/>} />
      <Route path="/hr" element={<HR/>} />
      <Route path="/feedback" element={<Feedback/>} />
    </Routes>
  </BrowserRouter>
)