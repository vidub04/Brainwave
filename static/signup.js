async function handleSignUp() {
    const msg = document.getElementById("authMsg");
    const btn = document.getElementById("signupBtn");

    const showMsg = (text, color) => {
        msg.style.display = "block";
        msg.style.color = color || "#f87171";
        msg.textContent = text;
    };

    const fullName = document.getElementById("fullName").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (!email || !password) {
        showMsg("Please enter an email and password.");
        return;
    }
    if (password.length < 6) {
        showMsg("Password must be at least 6 characters.");
        return;
    }
    if (password !== confirmPassword) {
        showMsg("Passwords do not match.");
        return;
    }

    if (!supabaseReady) {
        showMsg("Please wait, authentication is initializing...");
        return;
    }
    await supabaseReady;

    btn.disabled = true;
    btn.textContent = "Creating account...";

    try {
        const res = await fetch("/api/auth/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password, full_name: fullName || null })
        });
        const data = await res.json();

        if (!res.ok) {
            showMsg(data.detail || "Could not create account.");
            btn.disabled = false;
            btn.textContent = "Create Account";
            return;
        }

        // Account is created and auto-verified server-side — sign the user in immediately.
        const { error } = await supabaseClient.auth.signInWithPassword({ email, password });

        if (error) {
            showMsg("Account created! Please log in.", "#4ade80");
            btn.disabled = false;
            btn.textContent = "Create Account";
            setTimeout(() => { window.location.href = "/"; }, 1200);
            return;
        }

        window.location.href = "/app";
    } catch (e) {
        console.error("Signup error:", e);
        showMsg("Something went wrong. Please try again.");
        btn.disabled = false;
        btn.textContent = "Create Account";
    }
}
