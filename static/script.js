let accessToken = null;
let conversationId = null;
let questionCount = 1;

// Run on page load: enforce login, wire up the landing button, then
// restore the most recent conversation (if any)
(async function init() {
    accessToken = await requireSession();
    if (!accessToken) return; // requireSession already redirected to /login

    document.getElementById("startBtn").addEventListener("click", () => {
        document.getElementById("landing").style.display = "none";
        document.getElementById("interview").classList.remove("hidden");
        startTimer();
    });

    const res = await fetch("/conversations", {
        headers: { "Authorization": `Bearer ${accessToken}` }
    });
    const data = await res.json();

    if (data.conversations && data.conversations.length > 0) {
        conversationId = data.conversations[0].id;
        await loadHistory(conversationId);
    }
})();

function startTimer() {
    let seconds = 0;
    setInterval(() => {
        seconds++;
        const min = Math.floor(seconds / 60);
        const sec = seconds % 60;
        document.getElementById("timer").innerText =
            `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
    }, 1000);
}

async function loadHistory(id) {
    const res = await fetch(`/history/${id}`, {
        headers: { "Authorization": `Bearer ${accessToken}` }
    });
    const data = await res.json();

    const chatBox = document.getElementById("chatBox");
    // Keep the initial greeting, append real history after it
    data.messages.forEach(m => {
        appendMessage(m.role, m.content);
        if (m.role === "user") {
            questionCount = Math.min(questionCount + 1, 11);
        }
    });
    document.getElementById("questionNo").innerText = `Question ${questionCount} / 11`;
    chatBox.scrollTop = chatBox.scrollHeight;
}

function appendMessage(role, text) {
    const chatBox = document.getElementById("chatBox");
    const avatar = role === "user" ? "😊" : "🤖";
    chatBox.innerHTML += `
    <div class="message ${role === "user" ? "user" : "bot"}">
        <div class="avatar">${avatar}</div>
        <div class="bubble">${text}</div>
    </div>
    `;
}

async function sendPrompt() {
    const promptEl = document.getElementById("prompt");
    const chatBox = document.getElementById("chatBox");
    const text = promptEl.value.trim();
    if (text === "") return;

    appendMessage("user", text);
    promptEl.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    const res = await fetch("/generate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${accessToken}`
        },
        body: JSON.stringify({
            prompt: text,
            conversation_id: conversationId
        })
    });

    if (res.status === 401) {
        window.location.href = "/login";
        return;
    }

    const data = await res.json();
    conversationId = data.conversation_id;

    appendMessage("bot", data.response);
    chatBox.scrollTop = chatBox.scrollHeight;

    questionCount = Math.min(questionCount + 1, 11);
    document.getElementById("questionNo").innerText = `Question ${questionCount} / 11`;
}

async function uploadResume() {
    const input = document.getElementById("resumeInput");
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/resume/upload", {
        method: "POST",
        headers: { "Authorization": `Bearer ${accessToken}` },
        body: formData
    });

    if (!res.ok) {
        const err = await res.json();
        alert(`Resume upload failed: ${err.detail || "unknown error"}`);
        return;
    }

    appendMessage("bot", "📄 Got your resume — I'll tailor questions to your background.");
    document.getElementById("chatBox").scrollTop = document.getElementById("chatBox").scrollHeight;
}
