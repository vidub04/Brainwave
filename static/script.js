let accessToken = null;
let conversationId = null;
let questionCount = 1;
let selectedRole = null;
let timerInterval = null;
let voiceOutputEnabled = false;

// Run on page load: enforce login, wire up the landing button, then
// restore the most recent conversation (if any)

async function init() {

    await supabaseReady;

    accessToken = await requireSession();

    if (!accessToken) return;
    console.log("accessToken:", accessToken);





    // -----------------------------
    // Start Interview Button
    // -----------------------------

    document.getElementById("startBtn").addEventListener("click", async () => {

        const roleValue =
            document.getElementById("roleSelect").value;

        const customRole =
            document.getElementById("customRoleInput").value.trim();

        selectedRole =
            roleValue === "Other" && customRole
                ? customRole
                : roleValue;


        // Create a NEW interview session
        const res = await fetch("/app/conversations", {
            method: "POST",

            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${accessToken}`
            },

            body: JSON.stringify({
                role: selectedRole
            })
        });


        if (!res.ok) {

            const error = await res.text();

            console.error(
                "Failed to create conversation:",
                error
            );

            return;
        }


        const data = await res.json();


        // Store NEW conversation ID
        conversationId = data.conversation_id;


        // -----------------------------
        // Reset interview UI
        // -----------------------------

        const chatBox =
            document.getElementById("chatBox");

        chatBox.innerHTML = "";


        // Reset question count
        questionCount = 0;

        document.getElementById("questionNo").innerText =
            "Question 0 / 11";

        updateProgressBar();


        // -----------------------------
        // Open interview screen
        // -----------------------------

        document.getElementById("landing").style.display =
            "none";

        document.getElementById("interview").classList.remove(
            "hidden"
        );


        // Start timer
        startTimer();

        // Refresh the sidebar so the new interview shows up immediately
        await loadConversationList();

    });


    // -----------------------------
    // Role selector
    // -----------------------------

    document.getElementById("roleSelect")
        .addEventListener("change", (e) => {

            const customInput =
                document.getElementById("customRoleInput");

            if (e.target.value === "Other") {

                customInput.classList.remove("hidden");

                customInput.focus();

            } else {

                customInput.classList.add("hidden");

            }

        });


    toggleCodeEditor(false);

    // -----------------------------
    // Chat history sidebar
    // -----------------------------

    document.getElementById("newInterviewBtn").addEventListener("click", () => {
        document.getElementById("interview").classList.add("hidden");
        document.getElementById("landing").style.display = "flex";
    });

    await loadConversationList();
}


init();

async function testResume() {
    try {
        // Make sure Supabase is initialized
        await supabaseReady;

        // Get the current logged-in session
        const { data, error } = await supabaseClient.auth.getSession();

        if (error) {
            console.error("Session error:", error);
            return;
        }

        // Get access token
        const token = data.session?.access_token;

        if (!token) {
            console.error("User is not logged in");
            return;
        }

        // Call FastAPI
        const res = await fetch("/app/get-resume-info", {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        // Convert response to JSON
        const result = await res.json();

        console.log("Resume response:", result);

        if (!res.ok) {
            console.error("Resume request failed:", result);
            return;
        }

        // Resume data
        if (result.found) {
            console.log("Candidate resume:", result.resume);
        } else {
            console.log("No resume found");
        }

    } catch (error) {
        console.error("Error fetching resume:", error);
    }
}

//testing history

async function testHistory() {

    try {

        const res = await fetch("/app/test-history", {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${accessToken}`
            }
        });

        const result = await res.json();

        console.log("Interview history:", result);

    } catch (error) {

        console.error("History error:", error);

    }
}

//testing current state
async function testCurrentState() {

    const res = await fetch(
        `/app/test-state/${conversationId}`,
        {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${accessToken}`
            }
        }
    );

    const data = await res.json();

    console.log("CURRENT STATE:", data);
}
/*
(async function init() {

    await supabaseReady;
    accessToken = await requireSession();
    if (!accessToken) return; // requireSession already redirected to /login

    document.getElementById("startBtn").addEventListener("click", () => {
        const roleValue = document.getElementById("roleSelect").value;
        const customRole = document.getElementById("customRoleInput").value.trim();
        selectedRole = roleValue === "Other" && customRole ? customRole : roleValue;

        
        document.getElementById("landing").style.display = "none";
        document.getElementById("interview").classList.remove("hidden");
        startTimer();
        
    });

    document.getElementById("roleSelect").addEventListener("change", (e) => {
        const customInput = document.getElementById("customRoleInput");
        if (e.target.value === "Other") {
            customInput.classList.remove("hidden");
            customInput.focus();
        } else {
            customInput.classList.add("hidden");
        }
    });

    toggleCodeEditor(false);

    /*old code for viewing history of interviews
    
    const res = await fetch("/app/conversations", {
        headers: { "Authorization": `Bearer ${accessToken}` }
    });
    const data = await res.json();

    if (data.conversations && data.conversations.length > 0) {
        conversationId = data.conversations[0].id;
        await loadHistory(conversationId);
    }

    

    
    // Create a NEW interview session
    const res = await fetch("/app/conversations", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${accessToken}`
        },
        body: JSON.stringify({
            role: selectedRole
        })
    });

    const data = await res.json();

    // Store the NEW conversation ID
    conversationId = data.conversation_id;

    // Clear previous chat from UI
    const chatBox = document.getElementById("chatBox");
    chatBox.innerHTML = "";

    // Reset interview state
    questionCount = 0;

    document.getElementById("questionNo").innerText =
        "Question 0 / 11";

    // Show interview screen
    
    document.getElementById("landing").style.display = "none";
    document.getElementById("interview").classList.remove("hidden");

    startTimer();

    

})();

*/

function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    let seconds = 0;
    document.getElementById("timer").innerText = "00:00";
    timerInterval = setInterval(() => {
        seconds++;
        const min = Math.floor(seconds / 60);
        const sec = seconds % 60;
        document.getElementById("timer").innerText =
            `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
    }, 1000);
}

// ---------- Chat history sidebar ----------

async function loadConversationList() {
    const listEl = document.getElementById("conversationList");
    if (!listEl) return;

    const res = await fetch("/app/conversations", {
        headers: { "Authorization": `Bearer ${accessToken}` }
    });
    if (!res.ok) return;

    const data = await res.json();
    const conversations = data.conversations || [];

    if (conversations.length === 0) {
        listEl.innerHTML = `<p class="sidebar-empty">No interviews yet</p>`;
        return;
    }

    listEl.innerHTML = conversations.map(c => {
        const label = c.target_role || c.title || "Interview";
        const date = c.created_at
            ? new Date(c.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })
            : "";
        const activeClass = c.id === conversationId ? "active" : "";
        return `
        <div class="conversation-item ${activeClass}" data-id="${c.id}" data-role="${label}">
            <div class="conversation-item-title">${label}</div>
            <div class="conversation-item-date">${date}</div>
        </div>`;
    }).join("");

    listEl.querySelectorAll(".conversation-item").forEach(item => {
        item.addEventListener("click", () => {
            resumeConversation(item.dataset.id, item.dataset.role);
        });
    });
}

async function resumeConversation(id, role) {
    conversationId = id;
    selectedRole = role;
    questionCount = 0;

    const chatBox = document.getElementById("chatBox");
    chatBox.innerHTML = "";

    document.getElementById("landing").style.display = "none";
    document.getElementById("interview").classList.remove("hidden");

    await loadHistory(id);
    startTimer();

    document.querySelectorAll(".conversation-item").forEach(item => {
        item.classList.toggle("active", item.dataset.id === id);
    });
}

async function loadHistory(id) {
    const res = await fetch(`/app/history/${id}`, {
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
    updateProgressBar();
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

        speakText(parsed.message, parsed.speaker);

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

// ---------- Voice output (mutable — off by default) ----------

function toggleVoiceOutput() {
    voiceOutputEnabled = !voiceOutputEnabled;
    const btn = document.getElementById("voiceToggleBtn");
    if (btn) btn.innerText = voiceOutputEnabled ? "🔊 Voice" : "🔇 Voice";
    if (!voiceOutputEnabled && window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
}

function speakText(text, speaker) {
    if (!voiceOutputEnabled || !window.speechSynthesis) return;
    if (!text || !text.trim()) return;

    window.speechSynthesis.cancel(); // don't stack overlapping utterances
    const utterance = new SpeechSynthesisUtterance(text);

    // Distinct pitch/rate per persona so Alex and Ricky sound different,
    // without depending on browser-specific voice lists being available.
    if (speaker === "Ricky") {
        utterance.pitch = 1.3;
        utterance.rate = 1.02;
    } else {
        utterance.pitch = 0.85;
        utterance.rate = 0.98;
    }

    window.speechSynthesis.speak(utterance);
}

// ---------- Progress bar (mirrors "Question X / 11") ----------

function updateProgressBar() {
    const fill = document.getElementById("progressBarFill");
    if (!fill) return;
    const pct = Math.min(100, Math.max(0, (questionCount / 11) * 100));
    fill.style.width = `${pct}%`;
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

    const res = await fetch("/app/generate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${accessToken}`
        },
        body: JSON.stringify({
            prompt: text,
            conversation_id: conversationId,
            target_role: selectedRole
        })
    });

    if (res.status === 401) {
        window.location.href = "/";
        return;
    }

    const data = await res.json();
    conversationId = data.conversation_id;

    appendMessage("bot", data.response);
    chatBox.scrollTop = chatBox.scrollHeight;

    questionCount = Math.min(questionCount + 1, 11);
    document.getElementById("questionNo").innerText = `Question ${questionCount} / 11`;
    updateProgressBar();
}

async function uploadResume() {
    const input = document.getElementById("resumeInput");
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/app/resume/upload", {
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

