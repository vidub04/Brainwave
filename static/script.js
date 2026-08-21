let accessToken = null;
let interviewId = null;
let selectedRole = "Machine Learning Engineer";
let targetDuration = 30;
let totalQuestions = 8;
let currentQuestionIndex = 0;
let timerInterval = null;
let voiceOutputEnabled = false;
let uploadedResumeText = "";
let uploadedResumeStructured = null;
let isRecordingVoice = false;
let speechRecognizer = null;
let isCodeEditorOpen = false;

// ============================================================
// Initialization
// ============================================================

async function init() {
    await supabaseReady;
    accessToken = await requireSession();
    if (!accessToken) return;

    setupLandingControls();
    setupSpeechRecognition();
    await loadPastSessions();
}

function setupLandingControls() {
    const roleSelect = document.getElementById("roleSelect");
    const customRoleInput = document.getElementById("customRoleInput");
    const startBtn = document.getElementById("startBtn");

    roleSelect.addEventListener("change", (e) => {
        if (e.target.value === "Other") {
            customRoleInput.classList.remove("hidden");
            customRoleInput.focus();
        } else {
            customRoleInput.classList.add("hidden");
        }
    });

    startBtn.addEventListener("click", startAdaptiveInterviewSession);

    document.getElementById("newInterviewBtn").addEventListener("click", () => {
        document.getElementById("interview").classList.add("hidden");
        document.getElementById("landing").style.display = "flex";
        if (timerInterval) clearInterval(timerInterval);
    });
}

// ============================================================
// Resume Upload on Landing Page
// ============================================================

async function handleLandingResumeUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const statusPill = document.getElementById("resumeStatus");
    const fileNameDisplay = document.getElementById("fileNameDisplay");
    const skillsContainer = document.getElementById("parsedSkillsPills");

    statusPill.innerText = "Parsing...";
    statusPill.classList.add("loading");
    fileNameDisplay.innerText = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/app/resume/upload", {
            method: "POST",
            headers: { "Authorization": `Bearer ${accessToken}` },
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`Resume upload failed: ${err.detail || "Error processing file"}`);
            statusPill.innerText = "Error";
            return;
        }

        const data = await res.json();
        uploadedResumeStructured = data.structured || {};
        uploadedResumeText = data.raw_text || "";

        statusPill.innerHTML = `<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle; margin-right:4px;"><polyline points="20 6 9 17 4 12"/></svg>Attached`;
        statusPill.classList.remove("loading");
        statusPill.classList.add("attached");
        fileNameDisplay.innerHTML = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle; margin-right:6px;"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>${escapeHtml(file.name)} (${uploadedResumeStructured.years_experience || 2}+ yrs exp)`;

        // Render extracted skills pills
        const skills = uploadedResumeStructured.skills || [];
        if (skills.length > 0) {
            skillsContainer.innerHTML = skills.slice(0, 8).map(s => `<span class="skill-pill">${escapeHtml(s)}</span>`).join("");
            skillsContainer.classList.remove("hidden");
        }
    } catch (e) {
        console.error("Resume upload exception:", e);
        statusPill.innerText = "Failed";
    }
}

// ============================================================
// Start Adaptive Interview
// ============================================================

async function startAdaptiveInterviewSession() {
    const roleVal = document.getElementById("roleSelect").value;
    const customVal = document.getElementById("customRoleInput").value.trim();
    selectedRole = (roleVal === "Other" && customVal) ? customVal : roleVal;

    const durationVal = parseInt(document.getElementById("durationSelect").value, 10) || 30;
    const typeVal = document.getElementById("typeSelect").value;
    const jdText = document.getElementById("jdInput").value.trim();

    targetDuration = durationVal;
    document.getElementById("headerRole").innerText = selectedRole;

    // Show initial loading state on start button
    const startBtn = document.getElementById("startBtn");
    startBtn.disabled = true;
    startBtn.innerHTML = `<span>Synthesizing Interview Plan...</span>`;

    try {
        // 1. Create Interview Plan
        const createRes = await fetch("/api/interview/create", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${accessToken}`
            },
            body: JSON.stringify({
                role: selectedRole,
                job_description: jdText,
                resume_text: uploadedResumeText,
                resume_structured: uploadedResumeStructured,
                duration_minutes: durationVal,
                interview_type: typeVal
            })
        });

        if (!createRes.ok) {
            throw new Error(await createRes.text());
        }

        const createData = await createRes.json();
        interviewId = createData.interview_id;
        totalQuestions = createData.total_questions || 8;

        // 2. Start Interview & Fetch Question 1
        const startRes = await fetch(`/api/interview/${interviewId}/start`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${accessToken}` }
        });

        if (!startRes.ok) {
            throw new Error(await startRes.text());
        }

        const startData = await startRes.json();

        // 3. Switch Screen
        document.getElementById("landing").style.display = "none";
        document.getElementById("interview").classList.remove("hidden");
        document.getElementById("chatBox").innerHTML = "";

        currentQuestionIndex = 1;
        updateQuestionCounter(1, totalQuestions);
        updateDifficultyBadge(startData.current_difficulty || 2);
        updateStageBadge(startData.current_stage || "Technical Fundamentals");
        document.getElementById("currentFocusSkill").innerText = startData.question.skill || "Fundamentals";

        startTimer(durationVal * 60);

        // Append initial Question 1
        appendBotQuestion(startData.question);

        // Reset Decision Drawer
        document.getElementById("decisionLogList").innerHTML = `
            <div class="decision-entry initial">
                <div class="decision-step-badge">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                    <span>Interview Initialized</span>
                </div>
                <p><strong>Role:</strong> ${escapeHtml(selectedRole)}</p>
                <p><strong>Initial Focus:</strong> ${escapeHtml(startData.question.skill)}</p>
                <p><strong>Baseline Difficulty:</strong> Level ${startData.current_difficulty}/5</p>
            </div>
        `;

        await loadPastSessions();
    } catch (err) {
        console.error("Error starting adaptive interview:", err);
        alert(`Failed to start interview: ${err.message}`);
    } finally {
        startBtn.disabled = false;
        startBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg><span>Begin Adaptive Interview</span>`;
    }
}

// ============================================================
// Submit Candidate Answer
// ============================================================

async function sendPrompt() {
    const promptEl = document.getElementById("prompt");
    const codeEl = document.getElementById("codeInput");
    const answerText = promptEl.value.trim();
    const codeText = isCodeEditorOpen ? codeEl.value.trim() : null;

    if (!answerText && !codeText) return;

    // Stop microphone if currently recording
    if (isRecordingVoice) {
        toggleMicRecording();
    }

    // Append Candidate message to UI
    let fullUserDisplay = answerText;
    if (codeText) {
        const lang = document.getElementById("codeLanguage").value || "python";
        fullUserDisplay += (fullUserDisplay ? "\n\n" : "") + `\`\`\`${lang}\n${codeText}\n\`\`\``;
    }
    appendUserMessage(fullUserDisplay);

    promptEl.value = "";
    if (codeEl) codeEl.value = "";
    if (isCodeEditorOpen) toggleCodeEditorMode(false);

    // Show dynamic multi-step loading status
    showEvalLoading(true);

    try {
        const res = await fetch(`/api/interview/${interviewId}/answer`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${accessToken}`
            },
            body: JSON.stringify({
                answer: answerText || "Provided code solution",
                code: codeText
            })
        });

        if (res.status === 401) {
            window.location.href = "/";
            return;
        }

        if (!res.ok) {
            throw new Error(await res.text());
        }

        const data = await res.json();
        showEvalLoading(false);

        // Record entry in Decision Log Drawer
        appendDecisionLogEntry(data);

        // Update Skill Scores & Difficulty
        if (data.current_difficulty) {
            updateDifficultyBadge(data.current_difficulty);
        }
        if (data.current_stage) {
            updateStageBadge(data.current_stage);
        }

        // inside sendPrompt(), after receiving `data` from /answer:
        if (data.execution_result) {
            appendExecutionResultCard(data.execution_result);
        }

        function appendExecutionResultCard(exec) {
            const chatBox = document.getElementById("chatBox");
            const rows = exec.results.map(r => `
                <div class="test-case-row ${r.passed ? 'pass' : 'fail'}">
                    <span class="test-status-pill ${r.passed ? 'pass' : 'fail'}">
                        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            ${r.passed ? '<polyline points="20 6 9 17 4 12"/>' : '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'}
                        </svg>
                        ${r.passed ? "Passed" : "Failed"}
                    </span>
                    <span>Input: <code>${escapeHtml(JSON.stringify(r.input_args))}</code> → Expected: <code>${escapeHtml(JSON.stringify(r.expected_output))}</code>, Got: <code>${escapeHtml(JSON.stringify(r.actual_output))}</code></span>
                    ${r.error ? `<span class="test-error">${escapeHtml(r.error)}</span>` : ""}
                </div>
            `).join("");
            chatBox.innerHTML += `
            <div class="execution-result-card">
                <strong>${exec.passed_count}/${exec.total_count} test cases passed</strong>
                ${exec.runtime_error ? `<div class="test-error">${escapeHtml(exec.runtime_error)}</div>` : rows}
            </div>`;
        }

        // Check if interview completed
        if (data.is_completed) {
            currentQuestionIndex = totalQuestions;
            updateQuestionCounter(totalQuestions, totalQuestions);
            updateProgressBar(100);

            appendBotMessage({
                speaker: "Alex",
                message: "Excellent job completing the interview! I've synthesized your evaluation, diagnosed your skill breakdown, and generated your personalized preparation roadmap.",
                why_this_question: "Interview Completed"
            });

            if (data.report) {
                renderFinalReport(data.report);
            }
            return;
        }

        // Advance to Next Question
        currentQuestionIndex = (data.questions_asked || currentQuestionIndex) + 1;
        updateQuestionCounter(currentQuestionIndex, totalQuestions);
        updateProgressBar((currentQuestionIndex / totalQuestions) * 100);

        if (data.next_question) {
            document.getElementById("currentFocusSkill").innerText = data.next_question.skill || "Technical Depth";
            appendBotQuestion(data.next_question);
        }

    } catch (err) {
        showEvalLoading(false);
        console.error("Failed to process answer:", err);
        alert(`Error processing response: ${err.message}`);
    }
}

// ============================================================
// Message Rendering & Audio
// ============================================================

function appendUserMessage(text) {
    const chatBox = document.getElementById("chatBox");
    const codeMatch = text.match(/```(\w+)?\n([\s\S]*?)```/);
    let bubbleContent = "";

    if (codeMatch) {
        const textBefore = text.slice(0, codeMatch.index).trim();
        const code = codeMatch[2];
        const textAfter = text.slice(codeMatch.index + codeMatch[0].length).trim();
        
        if (textBefore) bubbleContent += `<p>${formatMessageText(textBefore)}</p>`;
        bubbleContent += `<pre class="code-bubble"><code>${escapeHtml(code)}</code></pre>`;
        if (textAfter) bubbleContent += `<p>${formatMessageText(textAfter)}</p>`;
    } else {
        bubbleContent = formatMessageText(text);
    }

    chatBox.innerHTML += `
    <div class="message user">
        <div class="avatar user-avatar" title="Candidate">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
            </svg>
        </div>
        <div class="bubble">${bubbleContent}</div>
    </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;
}

function getSpeakerAvatarHtml(speaker) {
    if (speaker === "Ricky") {
        return `
        <div class="avatar bot-avatar bot-ricky" title="Ricky · Behavioral & Leadership Lead">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
        </div>`;
    }
    return `
    <div class="avatar bot-avatar bot-alex" title="Alex · Technical Lead">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="4" width="16" height="16" rx="2"/>
            <rect x="9" y="9" width="6" height="6"/>
            <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>
        </svg>
    </div>`;
}

function appendBotQuestion(qItem) {
    const speaker = qItem.speaker || "Alex";
    const avatarHtml = getSpeakerAvatarHtml(speaker);
    const whyText = qItem.why_this_question || "";

    const whyBadgeHtml = whyText ? `
        <div class="why-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="bulb-icon"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg>
            <span><strong>Why this question?</strong> ${escapeHtml(whyText)}</span>
        </div>
    ` : "";

    const categoryTag = `<span class="q-meta-tag category">${escapeHtml(qItem.category || "Technical")}</span>`;
    const skillTag = `<span class="q-meta-tag skill">${escapeHtml(qItem.skill || "")}</span>`;

    const chatBox = document.getElementById("chatBox");
    chatBox.innerHTML += `
    <div class="message bot" data-speaker="${speaker}">
        ${avatarHtml}
        <div class="bubble">
            <div class="bubble-header">
                <span class="speaker-name">${speaker} (AI Interviewer)</span>
                <div class="q-meta-row">${categoryTag} ${skillTag}</div>
            </div>
            <div class="question-text">${formatMessageText(qItem.question)}</div>
            ${whyBadgeHtml}
        </div>
    </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;

        if (qItem.requires_code) {
            toggleCodeEditorMode(true);
            if (qItem.starter_code) {
                document.getElementById("codeInput").value = qItem.starter_code;
            }
            /*if (qItem.visible_test_cases && qItem.visible_test_cases.length) {
                renderVisibleTestCases(qItem.visible_test_cases);
            }*/
    }


    speakText(qItem.question, speaker);
}

function appendBotMessage(data) {
    const chatBox = document.getElementById("chatBox");
    const speaker = data.speaker || "Alex";
    const avatarHtml = getSpeakerAvatarHtml(speaker);
    chatBox.innerHTML += `
    <div class="message bot">
        ${avatarHtml}
        <div class="bubble">
            <div class="speaker-name">${speaker} (AI Interviewer)</div>
            <div>${formatMessageText(data.message)}</div>
        </div>
    </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;
    speakText(data.message, data.speaker);
}

function formatMessageText(text) {
    return escapeHtml(text).replace(/\n/g, "<br>");
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// ============================================================
// Speech-to-Text (Microphone) using Web Speech API
// ============================================================

function setupSpeechRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        const micBtn = document.getElementById("micBtn");
        if (micBtn) {
            micBtn.title = "Speech recognition not supported in this browser";
            micBtn.style.opacity = "0.6";
        }
        return;
    }

    speechRecognizer = new SpeechRec();
    speechRecognizer.continuous = true;
    speechRecognizer.interimResults = true;
    speechRecognizer.lang = "en-US";

    speechRecognizer.onresult = (event) => {
        let finalTranscript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript + " ";
            }
        }
        if (finalTranscript) {
            const promptEl = document.getElementById("prompt");
            promptEl.value += (promptEl.value ? " " : "") + finalTranscript.trim();
        }
    };

    speechRecognizer.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        if (isRecordingVoice) toggleMicRecording();
    };
}

function toggleMicRecording() {
    if (!speechRecognizer) {
        alert("Speech recognition is supported in Google Chrome, Edge, and modern browsers.");
        return;
    }

    const micBtn = document.getElementById("micBtn");
    const label = document.getElementById("micBtnLabel");

    if (!isRecordingVoice) {
        try {
            speechRecognizer.start();
            isRecordingVoice = true;
            micBtn.classList.add("recording");
            label.innerHTML = `<span class="rec-dot"></span><span>Listening... (Click to stop)</span>`;
        } catch (e) {
            console.error("Failed to start speech recognition:", e);
        }
    } else {
        speechRecognizer.stop();
        isRecordingVoice = false;
        micBtn.classList.remove("recording");
        label.innerText = "Voice Answer";
    }
}

// ============================================================
// Voice Text-to-Speech (Interviewer Voice)
// ============================================================

function toggleVoiceOutput() {
    voiceOutputEnabled = !voiceOutputEnabled;
    const btn = document.getElementById("voiceToggleBtn");
    if (btn) {
        if (voiceOutputEnabled) {
            btn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg><span id="voiceToggleLabel">Voice: ON</span>`;
        } else {
            btn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg><span id="voiceToggleLabel">Voice Muted</span>`;
        }
    }
    if (!voiceOutputEnabled && window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
}

function speakText(text, speaker) {
    if (!voiceOutputEnabled || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();

    // Clean markdown and quotes
    const clean = text.replace(/```[\s\S]*?```/g, " code sample omitted ").replace(/[#*`]/g, "");
    const utterance = new SpeechSynthesisUtterance(clean);
    
    if (speaker === "Ricky") {
        utterance.pitch = 1.25;
        utterance.rate = 1.05;
    } else {
        utterance.pitch = 0.9;
        utterance.rate = 0.98;
    }

    window.speechSynthesis.speak(utterance);
}

// ============================================================
// UI Badges & Dynamic State
// ============================================================

function updateDifficultyBadge(level) {
    const badge = document.getElementById("difficultyBadge");
    if (!badge) return;

    badge.className = `diff-badge diff-${level}`;
    const levelMap = {
        1: "Beginner",
        2: "Easy",
        3: "Intermediate",
        4: "Advanced",
        5: "Expert"
    };
    badge.innerHTML = `<span class="diff-signal diff-signal-${level}"></span><span>Level ${level}: ${levelMap[level] || 'Level ' + level}</span>`;
}

function updateStageBadge(stage) {
    const el = document.getElementById("stageBadge");
    if (el) el.innerText = stage;
}

function updateQuestionCounter(current, total) {
    const el = document.getElementById("questionNo");
    if (el) el.innerText = `Question ${current} / ${total}`;
}

function updateProgressBar(pct) {
    const fill = document.getElementById("progressBarFill");
    if (fill) fill.style.width = `${Math.min(100, Math.max(0, pct))}%`;
    const covEl = document.getElementById("coverageSummary");
    if (covEl) covEl.innerText = `Coverage: ${Math.round(pct)}%`;
}

function toggleCodeEditorMode(forceState) {
    isCodeEditorOpen = (forceState !== undefined) ? forceState : !isCodeEditorOpen;
    const panel = document.getElementById("codeEditorPanel");
    const label = document.getElementById("codeToggleLabel");

    if (isCodeEditorOpen) {
        panel.classList.remove("hidden");
        label.innerText = "Close Code Editor";
        document.getElementById("codeInput").focus();
    } else {
        panel.classList.add("hidden");
        label.innerText = "Add Code Solution";
    }
}

function showEvalLoading(show) {
    const el = document.getElementById("evalLoadingIndicator");
    const textEl = document.getElementById("evalLoadingText");
    if (!el) return;

    if (show) {
        el.classList.remove("hidden");
        const steps = [
            "Analyzing candidate answer...",
            "Evaluating technical depth & reasoning...",
            "Checking missing concepts & difficulty fit...",
            "Deciding next adaptation action..."
        ];
        let stepIdx = 0;
        textEl.innerText = steps[0];
        window._evalInterval = setInterval(() => {
            stepIdx = (stepIdx + 1) % steps.length;
            textEl.innerText = steps[stepIdx];
        }, 1200);
    } else {
        el.classList.add("hidden");
        if (window._evalInterval) clearInterval(window._evalInterval);
    }
}

function startTimer(durationSeconds) {
    if (timerInterval) clearInterval(timerInterval);
    let remaining = durationSeconds;
    const timerEl = document.getElementById("timer");

    function renderTime() {
        const min = Math.floor(remaining / 60);
        const sec = remaining % 60;
        timerEl.innerText = `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
    }

    renderTime();
    timerInterval = setInterval(() => {
        if (remaining > 0) {
            remaining--;
            renderTime();
        }
    }, 1000);
}

// ============================================================
// Developer & Hackathon Judge Decision Log Drawer
// ============================================================

function toggleDecisionDrawer() {
    const drawer = document.getElementById("decisionLogDrawer");
    drawer.classList.toggle("hidden");
}

function appendDecisionLogEntry(turnData) {
    const list = document.getElementById("decisionLogList");
    const empty = list.querySelector(".drawer-empty");
    if (empty) empty.remove();

    const ev = turnData.evaluation || {};
    const action = turnData.action_taken || "SWITCH_SKILL";
    const reason = turnData.decision_reason || turnData.why_this_question || "";

    const entryHtml = `
    <div class="decision-entry">
        <div class="decision-step-badge">Turn ${turnData.questions_asked || "•"} Evaluation</div>
        <div class="eval-metrics-row">
            <span class="metric">Tech: <strong>${ev.technical_score || 0}/10</strong></span>
            <span class="metric">Reasoning: <strong>${ev.reasoning_score || 0}/10</strong></span>
            <span class="metric">Overall: <strong>${ev.overall_score || 0}/10</strong></span>
        </div>
        ${ev.missing_concepts && ev.missing_concepts.length ? `
            <div class="detected-gap"><strong>Diagnosed Gaps:</strong> ${escapeHtml(ev.missing_concepts.join(", "))}</div>
        ` : ""}
        <div class="action-badge-row">
            <span class="action-tag">${escapeHtml(action)}</span>
            <span class="diff-tag">Diff Level: ${turnData.current_difficulty || 2}</span>
        </div>
        <div class="decision-rationale">${escapeHtml(reason)}</div>
    </div>
    `;

    list.insertAdjacentHTML("afterbegin", entryHtml);
}

// ============================================================
// Final Comprehensive Report Modal
// ============================================================

function renderFinalReport(report) {
    const modal = document.getElementById("reportModal");
    modal.classList.remove("hidden");

    document.getElementById("reportRoleSubtitle").innerText = `${report.candidate_role} · Assessment & Preparation Roadmap`;
    document.getElementById("reportOverallScore").innerText = Math.round(report.overall_score);

    const gradeBadge = document.getElementById("reportGradeBadge");
    gradeBadge.innerText = report.score_grade || "Hire";
    gradeBadge.className = `grade-badge grade-${(report.score_grade || "hire").toLowerCase().replace(/\s+/g, "-")}`;

    document.getElementById("reportExecutiveSummary").innerText = report.summary || "";

    // Skill Bars Breakdown
    const skillContainer = document.getElementById("reportSkillBars");
    skillContainer.innerHTML = Object.entries(report.skill_breakdown || {}).map(([skill, score]) => {
        const val = Math.min(100, Math.max(0, Math.round(score)));
        return `
        <div class="skill-bar-row">
            <span class="skill-label">${escapeHtml(skill)}</span>
            <div class="skill-bar-track">
                <div class="skill-bar-fill" style="width: ${val}%;"></div>
            </div>
            <span class="skill-val">${val}%</span>
        </div>
        `;
    }).join("");

    // Strengths & Weaknesses
    const strengthsList = document.getElementById("reportStrengthsList");
    strengthsList.innerHTML = (report.strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join("") || "<li>Demonstrated foundational problem solving</li>";

    const weaknessesList = document.getElementById("reportWeaknessesList");
    weaknessesList.innerHTML = (report.weaknesses || []).map(w => `<li>${escapeHtml(w)}</li>`).join("") || "<li>Continue expanding edge-case coverage</li>";

    // Evidence Cards
    const evidenceContainer = document.getElementById("reportEvidenceContainer");
    evidenceContainer.innerHTML = (report.evidence || []).map(ev => `
        <div class="evidence-card ${ev.severity ? ev.severity.toLowerCase() : 'moderate'}">
            <div class="evidence-header">
                <strong>Turn ${ev.turn_number}: ${escapeHtml(ev.skill_or_concept)}</strong>
                <span class="evidence-severity">${escapeHtml(ev.severity || "Moderate")}</span>
            </div>
            <div class="evidence-q"><em>"${escapeHtml(ev.question_asked)}"</em></div>
            <div class="evidence-quote"><strong>Candidate:</strong> "${escapeHtml(ev.candidate_answer_excerpt)}"</div>
            <div class="evidence-diag"><strong>Diagnosis:</strong> ${escapeHtml(ev.weakness_summary)}</div>
        </div>
    `).join("") || "<p>No critical conceptual gaps diagnosed.</p>";

    // 7 / 14 / 30 Day Plan
    const plan = report.preparation_plan || {};
    document.getElementById("plan7List").innerHTML = (plan.day_7_focus || []).map(p => `<li>${escapeHtml(p)}</li>`).join("");
    document.getElementById("plan14List").innerHTML = (plan.day_14_focus || []).map(p => `<li>${escapeHtml(p)}</li>`).join("");
    document.getElementById("plan30List").innerHTML = (plan.day_30_focus || []).map(p => `<li>${escapeHtml(p)}</li>`).join("");
}

function closeReportModal() {
    document.getElementById("reportModal").classList.add("hidden");
}

// ============================================================
// Session History Sidebar
// ============================================================

async function loadPastSessions() {
    const listEl = document.getElementById("conversationList");
    if (!listEl) return;

    try {
        const res = await fetch("/app/conversations", {
            headers: { "Authorization": `Bearer ${accessToken}` }
        });
        if (!res.ok) return;

        const data = await res.json();
        const convs = data.conversations || [];

        if (convs.length === 0) {
            listEl.innerHTML = `<p class="sidebar-empty">No past sessions yet</p>`;
            return;
        }

        listEl.innerHTML = convs.map(c => `
            <div class="conversation-item ${c.id === interviewId ? 'active' : ''}" data-id="${c.id}">
                <div class="conversation-item-title">${escapeHtml(c.target_role || c.title || "Interview")}</div>
                <div class="conversation-item-date">${c.created_at ? new Date(c.created_at).toLocaleDateString() : ""}</div>
            </div>
        `).join("");

        listEl.querySelectorAll(".conversation-item").forEach(item => {
            item.addEventListener("click", () => resumePastSession(item.dataset.id));
        });
    } catch (e) {
        console.error("Error loading past sessions:", e);
    }
}

async function resumePastSession(id) {
    try {
        interviewId = id;
        const res = await fetch(`/api/interview/${id}/resume`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${accessToken}` }
        });

        if (!res.ok) {
            // Fallback to history
            await loadLegacyHistory(id);
            return;
        }

        const data = await res.json();
        selectedRole = data.role || "Software Engineer";
        document.getElementById("headerRole").innerText = selectedRole;

        document.getElementById("landing").style.display = "none";
        document.getElementById("interview").classList.remove("hidden");
        document.getElementById("chatBox").innerHTML = "";

        updateDifficultyBadge(data.current_difficulty || 2);
        updateStageBadge(data.current_stage || "Technical Fundamentals");
        updateQuestionCounter(data.questions_asked || 1, totalQuestions);

        await loadLegacyHistory(id);
        startTimer(30 * 60);
    } catch (e) {
        console.error("Failed to resume session:", e);
    }
}

async function loadLegacyHistory(id) {
    const res = await fetch(`/app/history/${id}`, {
        headers: { "Authorization": `Bearer ${accessToken}` }
    });
    const data = await res.json();
    const chatBox = document.getElementById("chatBox");
    chatBox.innerHTML = "";

    (data.messages || []).forEach(m => {
        if (m.role === "user") {
            appendUserMessage(m.content);
        } else {
            // Parse speaker and question text
            const text = m.content.replace(/^\[SPEAKER:[^\]]+\]\[DIFFICULTY:[^\]]+\](?:\[CODE:[^\]]+\])?\s*/, "");
            appendBotMessage({ speaker: "Alex", message: text });
        }
    });
}

init();
