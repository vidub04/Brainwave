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

    toggleCodeEditor(false);

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

    if (role !== "user") {
        const parsed = parseBotMessage(text);

        if (parsed.difficulty && parsed.difficulty !== "final") {
            updateDifficultyBadge(parsed.difficulty);
        }

        const avatar = parsed.speaker === "Ricky" ? "👔" : "🧑‍💻";
        const name = parsed.speaker || "Interviewer";

        chatBox.innerHTML += `
        <div class="message bot" data-speaker="${name}">
            <div class="avatar">${avatar}</div>
            <div class="bubble">
                <div class="speaker-name">${name}</div>
                ${formatMessageText(parsed.message)}
            </div>
        </div>
        `;

        if (parsed.scorecard) {
            renderScorecard(parsed.scorecard);
        }

        toggleCodeEditor(parsed.codeRequired === true);
        return;
    }

    // A user "message" containing a fenced code block gets rendered as code
    const codeBlockMatch = text.match(/```[\w]*\n?([\s\S]*?)```/);
    const bubbleContent = codeBlockMatch
        ? `<pre class="code-bubble"><code>${escapeHtml(codeBlockMatch[1].trim())}</code></pre>`
        : formatMessageText(text);

    chatBox.innerHTML += `
    <div class="message user">
        <div class="avatar">😊</div>
        <div class="bubble">${bubbleContent}</div>
    </div>
    `;
}

function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

// Splits a raw bot reply into: speaker, difficulty, visible message text,
// and (on the final message) the structured scorecard JSON.
function parseBotMessage(raw) {
    let text = raw;
    let speaker = null;
    let difficulty = null;
    let scorecard = null;

    const metaMatch = text.match(/^\[SPEAKER:(Alex|Ricky)\]\[DIFFICULTY:(rising|steady|easing|final)\](?:\[CODE:(true|false)\])?\s*/);
    let codeRequired = false;
    if (metaMatch) {
        speaker = metaMatch[1];
        difficulty = metaMatch[2];
        codeRequired = metaMatch[3] === "true";
        text = text.slice(metaMatch[0].length).trim();
    }

    const jsonMatch = text.match(/```json\s*([\s\S]*?)```/);
    if (jsonMatch) {
        try {
            scorecard = JSON.parse(jsonMatch[1]);
        } catch (e) {
            scorecard = null; // model produced malformed JSON — fail gracefully, just skip the visual
        }
        text = text.slice(0, jsonMatch.index).trim();
    }

    return { speaker, difficulty, message: text, scorecard, codeRequired };
}

function formatMessageText(text) {
    // Basic newline -> <br> so paragraph breaks show up in the bubble
    return text.replace(/\n/g, "<br>");
}

function updateDifficultyBadge(difficulty) {
    const badge = document.getElementById("difficultyBadge");
    if (!badge) return;
    const labels = {
        rising: "🔺 Difficulty: Rising",
        steady: "➖ Difficulty: Steady",
        easing: "🔻 Difficulty: Easing",
    };
    badge.innerText = labels[difficulty] || "Difficulty: Steady";
}

function toggleCodeEditor(show) {
    const panel = document.getElementById("codeEditorPanel");
    const textInput = document.getElementById("prompt");
    const sendBtn = document.getElementById("sendTextBtn");
    if (!panel) return;

    if (show) {
        panel.classList.remove("hidden");
        textInput.classList.add("hidden");
        sendBtn.classList.add("hidden");
    } else {
        panel.classList.add("hidden");
        textInput.classList.remove("hidden");
        sendBtn.classList.remove("hidden");
    }
}

async function submitCode() {
    const codeInput = document.getElementById("codeInput");
    const langSelect = document.getElementById("codeLanguage");
    const code = codeInput.value.trim();
    if (code === "") return;

    const language = langSelect.value;
    const wrapped = "```" + language + "\n" + code + "\n```";

    await sendPromptText(wrapped);
    codeInput.value = "";
}

function renderScorecard(data) {
    const chatBox = document.getElementById("chatBox");
    const scores = data.scorecard || {};

    const labelMap = {
        technical_knowledge: "Technical Knowledge",
        problem_solving: "Problem Solving",
        core_cs_fundamentals: "Core CS Fundamentals",
        project_knowledge: "Project Knowledge",
        communication: "Communication",
        confidence: "Confidence",
        leadership: "Leadership",
        behavioral_skills: "Behavioral Skills",
    };

    const barsHtml = Object.entries(labelMap).map(([key, label]) => {
        const value = Math.max(0, Math.min(10, Number(scores[key]) || 0));
        return `
        <div class="score-row">
            <span class="score-label">${label}</span>
            <div class="score-bar"><div class="score-fill" style="width:${value * 10}%"></div></div>
            <span class="score-value">${value}/10</span>
        </div>`;
    }).join("");

    const listHtml = (title, items) => {
        if (!items || !items.length) return "";
        return `<div class="score-list"><h4>${title}</h4><ul>${items.map(i => `<li>${i}</li>`).join("")}</ul></div>`;
    };

    const recClass = (data.recommendation || "").toLowerCase().replace(/\s+/g, "-");

    chatBox.innerHTML += `
    <div class="scorecard-card">
        <h3>📊 Interview Scorecard</h3>
        ${barsHtml}
        ${listHtml("Strengths", data.strengths)}
        ${listHtml("Areas for Improvement", data.areas_for_improvement)}
        ${listHtml("Recommended Study Topics", data.study_topics)}
        <div class="recommendation-badge ${recClass}">${data.recommendation || "—"}</div>
    </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendPrompt() {
    const promptEl = document.getElementById("prompt");
    const text = promptEl.value.trim();
    if (text === "") return;
    promptEl.value = "";
    await sendPromptText(text);
}

// Shared by both the plain-text send button and the code editor's submit button.
async function sendPromptText(text) {
    const chatBox = document.getElementById("chatBox");

    appendMessage("user", text);
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
