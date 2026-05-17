let datasetId = null;
let token = localStorage.getItem("token");

const el = id => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  // Redirect unauthenticated users away from the chat page
  if (document.getElementById("chat") && !token) {
    window.location.href = "/login";
    return;
  }

  // Welcome message on chat page load
  if (document.getElementById("chat")) {
    addMessage(
      "bot",
      "👋 Hi, I'm <b>AskSheets</b>. Upload a CSV, Excel, or PDF and ask questions about your data — or just chat with me."
    );
  }

  // ── Login ──────────────────────────────────────────────────────────────────
  const loginForm = el("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async e => {
      e.preventDefault();
      try {
        const res = await fetch("/login", {
          method: "POST",
          body: new FormData(loginForm),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Login failed" }));
          throw new Error(err.detail || "Login failed");
        }
        const { access_token } = await res.json();
        localStorage.setItem("token", access_token);
        token = access_token;
        window.location.href = "/static/chat.html";
      } catch (err) {
        showError("loginError", err.message);
      }
    });
  }

  // ── Signup ─────────────────────────────────────────────────────────────────
  const signupForm = el("signupForm");
  if (signupForm) {
    signupForm.addEventListener("submit", async e => {
      e.preventDefault();
      try {
        const res = await fetch("/signup", {
          method: "POST",
          body: new FormData(signupForm),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Signup failed" }));
          throw new Error(err.detail || "Signup failed");
        }
        window.location.href = "/login";
      } catch (err) {
        showError("signupError", err.message);
      }
    });
  }

  // ── File picker — show selected filename ──────────────────────────────────
  const fileInput = el("file");
  const fileLabel = el("fileLabel");
  if (fileInput && fileLabel) {
    fileInput.addEventListener("change", () => {
      fileLabel.textContent = fileInput.files[0]?.name || "";
    });
  }

  // ── Upload ─────────────────────────────────────────────────────────────────
  const btnUpload = el("btnUpload");
  if (btnUpload) {
    btnUpload.addEventListener("click", async () => {
      const f = fileInput?.files[0];
      if (!f) return addMessage("bot", "⚠️ Please select a file first.");

      addMessage("bot", `⏳ Uploading <b>${f.name}</b>…`);

      const fd = new FormData();
      fd.append("file", f);

      try {
        const res = await fetch("/upload", {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: fd,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Upload failed" }));
          throw new Error(err.detail);
        }
        const j = await res.json();
        datasetId = j.dataset_id;
        addMessage(
          "bot",
          `✅ <b>${f.name}</b> loaded — ${j.rows.toLocaleString()} rows, ${j.columns.length} columns.<br>` +
          `Columns: <code>${j.columns.join(", ")}</code>`
        );
        if (fileLabel) fileLabel.textContent = "";
      } catch (err) {
        addMessage("bot", `⚠️ Upload failed: ${err.message}`);
      }
    });
  }

  // ── Ask ────────────────────────────────────────────────────────────────────
  const btnAsk = el("btnAsk");
  const queryInput = el("query");

  async function sendQuestion() {
    const q = queryInput?.value.trim();
    if (!q) return;
    addMessage("user", q);
    queryInput.value = "";

    const thinkingId = addMessage("bot", "⏳ Thinking…", true);

    try {
      const res = await fetch("/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ query: q, dataset_id: datasetId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail);
      }
      const j = await res.json();
      removeMessage(thinkingId);
      addMessage("bot", j.answer);
    } catch (err) {
      removeMessage(thinkingId);
      addMessage("bot", `⚠️ ${err.message}`);
    }
  }

  if (btnAsk) btnAsk.addEventListener("click", sendQuestion);

  // Ctrl+Enter or Cmd+Enter to send
  if (queryInput) {
    queryInput.addEventListener("keydown", e => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        sendQuestion();
      }
    });
  }

  // ── Logout ─────────────────────────────────────────────────────────────────
  const logoutBtn = el("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("token");
      token = null;
      window.location.href = "/login";
    });
  }
});


// ── Helpers ───────────────────────────────────────────────────────────────────

let _msgCounter = 0;

function addMessage(sender, html, ephemeral = false) {
  const chat = el("chat");
  const id = `msg-${++_msgCounter}`;
  const div = document.createElement("div");
  div.className = `msg ${sender}`;
  div.id = id;
  div.innerHTML = `<div class="bubble">${html}</div>`;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return id;
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function showError(targetId, message) {
  const target = document.getElementById(targetId);
  if (target) {
    target.textContent = message;
    target.style.display = "block";
  } else {
    alert(message);
  }
}