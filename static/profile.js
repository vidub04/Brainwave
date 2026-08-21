let profileAccessToken = null;

(async function init() {
    await supabaseReady;
    profileAccessToken = await requireSession();
    if (!profileAccessToken) return;

    await loadProfile();

    document.getElementById("resumeUploadInput").addEventListener("change", handleResumeUpload);
})();

async function loadProfile() {
    try {
        const res = await fetch("/app/profile", {
            headers: { "Authorization": `Bearer ${profileAccessToken}` }
        });

        if (!res.ok) {
            document.getElementById("profileError").classList.remove("hidden");
            return;
        }

        const data = await res.json();
        renderIdentity(data);
        renderStats(data.stats || {});
        renderResume(data.resume);
    } catch (e) {
        console.error("Failed to load profile:", e);
        document.getElementById("profileError").classList.remove("hidden");
    }
}

function initials(nameOrEmail) {
    const clean = (nameOrEmail || "").trim();
    if (!clean) return "?";
    const parts = clean.split(/\s+/).filter(Boolean);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function renderIdentity(data) {
    const fullName = (data.full_name || "").trim();
    const displayName = fullName || (data.email ? data.email.split("@")[0] : "Candidate");

    document.getElementById("profileAvatar").textContent = initials(fullName || data.email);
    document.getElementById("profileName").textContent = displayName;
    document.getElementById("profileEmail").textContent = data.email || "";

    const joined = data.created_at
        ? new Date(data.created_at).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" })
        : null;
    document.getElementById("profileJoined").textContent = joined ? `Member since ${joined}` : "";
}

function renderStats(stats) {
    document.getElementById("statTotalInterviews").textContent = stats.total_interviews ?? 0;
    document.getElementById("statAvgScore").textContent = stats.avg_score != null ? `${stats.avg_score}/10` : "—";
    document.getElementById("statLastInterview").textContent = stats.last_interview_at
        ? new Date(stats.last_interview_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
        : "—";
}

function renderResume(resume) {
    const empty = document.getElementById("resumeEmpty");
    const details = document.getElementById("resumeDetails");
    const fileNameEl = document.getElementById("resumeFileName");

    if (!resume || !resume.structured) {
        fileNameEl.textContent = "No résumé uploaded yet";
        empty.classList.remove("hidden");
        details.classList.add("hidden");
        return;
    }

    fileNameEl.textContent = `📄 ${resume.filename || "Uploaded résumé"}`;
    empty.classList.add("hidden");
    details.classList.remove("hidden");

    const s = resume.structured;
    document.getElementById("resumeCandidateName").textContent = s.name || "—";
    document.getElementById("resumeCurrentRole").textContent = s.current_role || "—";
    document.getElementById("resumeYearsExp").textContent =
        s.years_experience != null ? `${s.years_experience}+ years` : "—";
    document.getElementById("resumeSummary").textContent = s.summary || "";

    const skillsEl = document.getElementById("resumeSkills");
    const skills = s.skills || [];
    skillsEl.innerHTML = skills.length
        ? skills.map(sk => `<span class="skill-pill">${escapeHtml(sk)}</span>`).join("")
        : `<span class="empty-hint">No skills extracted</span>`;

    const eduEl = document.getElementById("resumeEducation");
    const education = s.education || [];
    eduEl.innerHTML = education.length
        ? education.map(ed => `<li>${escapeHtml(ed)}</li>`).join("")
        : `<li class="empty-hint">Not listed</li>`;
}

async function handleResumeUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const status = document.getElementById("resumeUploadStatus");
    status.textContent = "Uploading & parsing...";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/app/resume/upload", {
            method: "POST",
            headers: { "Authorization": `Bearer ${profileAccessToken}` },
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            status.textContent = err.detail || "Upload failed.";
            return;
        }

        const data = await res.json();
        status.textContent = "✓ Résumé updated";
        renderResume({ filename: file.name, structured: data.structured });
    } catch (e) {
        console.error("Resume upload failed:", e);
        status.textContent = "Upload failed. Try again.";
    }
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
