let supabaseClient = null;

async function create_client() {
    try {
        const res = await fetch("/config");
        const data = await res.json();

        supabaseClient = window.supabase.createClient(
            data.supabase_url,
            data.supabase_anon_key
        );

        console.log("Supabase initialized successfully");
        return supabaseClient;
    } catch (err) {
        console.error("Failed to initialize Supabase client:", err);
        return null;
    }
}

const supabaseReady = create_client();

function showAuthMessage(text, isError = false) {
    const msg = document.getElementById("authMsg");
    if (!msg) return;
    msg.textContent = text;
    msg.style.color = isError ? "#f87171" : "#4ade80";
    msg.style.display = "block";
}

async function signUp() {
    await supabaseReady;
    const emailEl = document.getElementById("email");
    const passwordEl = document.getElementById("password");
    const email = emailEl.value.trim();
    const password = passwordEl.value.trim();

    if (!email || !password) {
        showAuthMessage("Please enter both email and password.", true);
        return;
    }

    if (password.length < 6) {
        showAuthMessage("Password must be at least 6 characters.", true);
        return;
    }

    showAuthMessage("Creating your account...", false);

    try {
        // Step 1: Use backend auto-confirm signup to bypass free-tier SMTP rate limits
        const res = await fetch("/api/auth/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (!res.ok) {
            // If backend returned error, check message
            showAuthMessage(data.detail || "Signup failed. Please try again.", true);
            return;
        }

        showAuthMessage("Account verified! Logging you in...", false);

        // Step 2: Immediately sign in and acquire session token
        const { data: authData, error: loginError } = await supabaseClient.auth.signInWithPassword({
            email,
            password
        });

        if (loginError) {
            showAuthMessage(`Account created! Please click 'Log In' to proceed (${loginError.message}).`, false);
            return;
        }

        showAuthMessage("Success! Redirecting to interview workspace...", false);
        setTimeout(() => {
            window.location.href = "/app";
        }, 500);

    } catch (err) {
        console.error("SignUp error:", err);
        showAuthMessage(`Signup failed: ${err.message || "Network error"}`, true);
    }
}

async function signIn() {
    await supabaseReady;
    const emailEl = document.getElementById("email");
    const passwordEl = document.getElementById("password");
    const email = emailEl.value.trim();
    const password = passwordEl.value.trim();

    if (!email || !password) {
        showAuthMessage("Please enter both email and password.", true);
        return;
    }

    showAuthMessage("Authenticating...", false);

    try {
        const { data, error } = await supabaseClient.auth.signInWithPassword({
            email,
            password
        });

        if (error) {
            showAuthMessage(error.message || "Invalid email or password.", true);
            return;
        }

        showAuthMessage("Success! Redirecting...", false);
        window.location.href = "/app";
    } catch (err) {
        console.error("SignIn error:", err);
        showAuthMessage(`Login error: ${err.message}`, true);
    }
}

async function quickDemoLogin() {
    await supabaseReady;
    showAuthMessage("Logging in with 1-Click Demo Candidate account...", false);

    try {
        const res = await fetch("/api/auth/demo-login", { method: "POST" });
        const creds = await res.json();

        const { data, error } = await supabaseClient.auth.signInWithPassword({
            email: creds.email,
            password: creds.password
        });

        if (error) {
            // Fallback: try signup if first time
            await fetch("/api/auth/signup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(creds)
            });
            const retry = await supabaseClient.auth.signInWithPassword(creds);
            if (retry.error) {
                showAuthMessage(retry.error.message, true);
                return;
            }
        }

        window.location.href = "/app";
    } catch (e) {
        console.error("Demo login error:", e);
        showAuthMessage("Demo login failed. Please enter your email and password.", true);
    }
}

async function signOut() {
    await supabaseReady;
    if (supabaseClient) {
        await supabaseClient.auth.signOut();
    }
    window.location.href = "/";
}

// Returns the current access token, or redirects to /login if there isn't one.
async function requireSession() {
    await supabaseReady;
    if (!supabaseClient) {
        window.location.href = "/";
        return null;
    }

    const { data: { session } } = await supabaseClient.auth.getSession();
    if (!session) {
        window.location.href = "/";
        return null;
    }
    return session.access_token;
}
