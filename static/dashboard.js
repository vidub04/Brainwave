const CATEGORY_LABELS = {
    technical_knowledge: "Technical Knowledge",
    problem_solving: "Problem Solving",
    core_cs_fundamentals: "Core CS Fundamentals",
    project_knowledge: "Project Knowledge",
    communication: "Communication",
    confidence: "Confidence",
    leadership: "Leadership",
    behavioral_skills: "Behavioral Skills",
};

const CATEGORY_COLORS = {
    technical_knowledge: "#2D9CDB",
    problem_solving: "#0EBB8A",
    core_cs_fundamentals: "#A78BFA",
    project_knowledge: "#F59E0B",
    communication: "#EF4444",
    confidence: "#EC4899",
    leadership: "#14B8A6",
    behavioral_skills: "#F472B6",
};

(async function init() {
    await supabaseReady;
    const accessToken = await requireSession();
    if (!accessToken) return;

    const res = await fetch("/app/progress", {
        headers: { "Authorization": `Bearer ${accessToken}` }
    });

    if (!res.ok) {
        document.getElementById("emptyState").classList.remove("hidden");
        document.getElementById("emptyState").innerText = "Couldn't load your progress right now — try refreshing.";
        return;
    }

    const data = await res.json();
    const scorecards = data.scorecards || [];

    if (scorecards.length === 0) {
        document.getElementById("emptyState").classList.remove("hidden");
        return;
    }

    renderSummary(scorecards);
    renderChart(scorecards);
    renderSessionTable(scorecards);
})();

function average(scorecards, key) {
    const values = scorecards.map(s => Number(s[key]) || 0);
    return values.reduce((a, b) => a + b, 0) / values.length;
}

function overallScore(sc) {
    const keys = Object.keys(CATEGORY_LABELS);
    const values = keys.map(k => Number(sc[k]) || 0);
    return values.reduce((a, b) => a + b, 0) / keys.length;
}

function renderSummary(scorecards) {
    const el = document.getElementById("summaryRow");
    el.classList.remove("hidden");

    const totalSessions = scorecards.length;
    const avgOverall = (scorecards.reduce((sum, sc) => sum + overallScore(sc), 0) / totalSessions).toFixed(1);

    const first = overallScore(scorecards[0]);
    const last = overallScore(scorecards[scorecards.length - 1]);
    const delta = (last - first).toFixed(1);
    const deltaLabel = delta > 0 ? `+${delta}` : delta;
    const deltaClass = delta > 0 ? "trend-up" : (delta < 0 ? "trend-down" : "trend-flat");

    el.innerHTML = `
        <div class="summary-stat">
            <div class="summary-value">${totalSessions}</div>
            <div class="summary-label">Interviews Completed</div>
        </div>
        <div class="summary-stat">
            <div class="summary-value">${avgOverall}/10</div>
            <div class="summary-label">Average Score</div>
        </div>
        <div class="summary-stat">
            <div class="summary-value ${deltaClass}">${deltaLabel}</div>
            <div class="summary-label">Change Since First Session</div>
        </div>
    `;
}

function renderChart(scorecards) {
    if (scorecards.length < 2) return; // need at least 2 points for a trend line

    document.getElementById("chartCard").classList.remove("hidden");
    const svg = document.getElementById("trendChart");
    const legend = document.getElementById("chartLegend");

    const padding = { top: 20, right: 20, bottom: 40, left: 40 };
    const width = 900 - padding.left - padding.right;
    const height = 320 - padding.top - padding.bottom;
    const n = scorecards.length;
    const stepX = n > 1 ? width / (n - 1) : 0;

    let svgContent = "";

    // gridlines + y-axis labels (0-10)
    for (let i = 0; i <= 5; i++) {
        const y = padding.top + height - (i * 2 * height / 10);
        svgContent += `<line x1="${padding.left}" y1="${y}" x2="${padding.left + width}" y2="${y}" stroke="#374151" stroke-width="1"/>`;
        svgContent += `<text x="${padding.left - 10}" y="${y + 4}" fill="#9ca3af" font-size="11" text-anchor="end">${i * 2}</text>`;
    }

    // one line per category
    Object.keys(CATEGORY_LABELS).forEach(key => {
        const color = CATEGORY_COLORS[key];
        const points = scorecards.map((sc, i) => {
            const value = Number(sc[key]) || 0;
            const x = padding.left + i * stepX;
            const y = padding.top + height - (value * height / 10);
            return `${x},${y}`;
        });
        svgContent += `<polyline points="${points.join(" ")}" fill="none" stroke="${color}" stroke-width="2.5" opacity="0.85"/>`;
        scorecards.forEach((sc, i) => {
            const value = Number(sc[key]) || 0;
            const x = padding.left + i * stepX;
            const y = padding.top + height - (value * height / 10);
            svgContent += `<circle cx="${x}" cy="${y}" r="3.5" fill="${color}"/>`;
        });
    });

    // x-axis session labels
    scorecards.forEach((sc, i) => {
        const x = padding.left + i * stepX;
        svgContent += `<text x="${x}" y="${padding.top + height + 22}" fill="#9ca3af" font-size="11" text-anchor="middle">#${i + 1}</text>`;
    });

    svg.innerHTML = svgContent;

    legend.innerHTML = Object.entries(CATEGORY_LABELS).map(([key, label]) => `
        <span class="legend-item"><span class="legend-dot" style="background:${CATEGORY_COLORS[key]}"></span>${label}</span>
    `).join("");
}

function renderSessionTable(scorecards) {
    document.getElementById("sessionTable").classList.remove("hidden");
    const container = document.getElementById("sessionRows");

    const recClass = (rec) => (rec || "").toLowerCase().replace(/\s+/g, "-");

    container.innerHTML = scorecards.slice().reverse().map((sc, idx) => {
        const sessionNum = scorecards.length - idx;
        const date = sc.created_at ? new Date(sc.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
        const score = overallScore(sc).toFixed(1);
        return `
        <div class="session-row">
            <span class="session-num">#${sessionNum}</span>
            <span class="session-role">${sc.target_role || "General"}</span>
            <span class="session-date">${date}</span>
            <span class="session-score">${score}/10</span>
            <span class="recommendation-badge ${recClass(sc.recommendation)}">${sc.recommendation || "—"}</span>
        </div>`;
    }).join("");
}
