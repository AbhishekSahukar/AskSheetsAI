let datasetId = null;
let token = localStorage.getItem("token");

const el = id => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  // Redirect to login if no token (on chat page)
  if (document.body.className !== "auth-body" && !token) {
    window.location.href = "/static/login.html";
  }

  // If chat page, show welcome message once
  if (document.getElementById("chat")) {
    addMessage("bot", "👋 Hi, I’m <b>AskSheets</b>. You can upload a file (Excel, CSV, PDF) or just chat with me. I’ll help you with analysis and general questions.");
  }

  // ---- LOGIN ----
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async e => {
      e.preventDefault();
      const username = el("username").value;
      const password = el("password").value;

      try {
        const res = await fetch("/login", {
          method: "POST",
          body: new FormData(loginForm),
        });
        if (!res.ok) throw new Error(await res.text());

        const j = await res.json();
        token = j.access_token;
        localStorage.setItem("token", token);
        window.location.href = "/static/chat.html";
      } catch (err) {
        alert("Login failed: " + err.message);
      }
    });
  }

  // ---- SIGNUP ----
  const signupForm = document.getElementById("signupForm");
  if (signupForm) {
    signupForm.addEventListener("submit", async e => {
      e.preventDefault();

      try {
        const res = await fetch("/signup", {
          method: "POST",
          body: new FormData(signupForm),
        });
        if (!res.ok) throw new Error(await res.text());

        alert("✅ Signup successful! Please log in.");
        window.location.href = "/static/login.html";
      } catch (err) {
        alert("Signup failed: " + err.message);
      }
    });
  }

  // ---- UPLOAD ----
  const btnUpload = el("btnUpload");
  if (btnUpload) {
    btnUpload.addEventListener("click", async () => {
      if (!token) return alert("Please log in first!");
      const f = el("file").files[0];
      if (!f) return alert("Pick a file");

      const fd = new FormData();
      fd.append("file", f);

      try {
        const res = await fetch("/upload", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
          body: fd
        });
        if (!res.ok) throw new Error(await res.text());

        const j = await res.json();
        datasetId = j.dataset_id;
        addMessage("bot", j.msg || `✅ File uploaded. Columns: ${j.columns}`);
      } catch (err) {
        alert("Upload failed: " + err.message);
      }
    });
  }

  // ---- ASK ----
  const btnAsk = el("btnAsk");
  if (btnAsk) {
    btnAsk.addEventListener("click", async () => {
      const q = el("query").value.trim();
      if (!q) return;
      addMessage("user", q);
      el("query").value = "";

      try {
        const res = await fetch("/ask", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ query: q, dataset_id: datasetId })
        });
        if (!res.ok) throw new Error(await res.text());

        const j = await res.json();
        addMessage("bot", j.answer);
      } catch (err) {
        addMessage("bot", "⚠️ Failed to get answer: " + err.message);
      }
    });
  }

  // ---- LOGOUT ----
  const logoutBtn = el("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("token");
      window.location.href = "/static/login.html";
    });
  }
});

// Helper: append chat bubbles
function addMessage(sender, text) {
  const chat = el("chat");
  const msg = document.createElement("div");
  msg.className = `msg ${sender}`;
  msg.innerHTML = `<div class="bubble">${text}</div>`;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}
