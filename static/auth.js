const config = await fetch("/config").then(res => res.json());

const SUPABASE_URL = config.supabase_url;
const SUPABASE_ANON_KEY = config.supabase_anon_key;


const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function signUp() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const { error } = await supabaseClient.auth.signUp({ email, password });
    const msg = document.getElementById("authMsg");
    if (error) {
        msg.textContent = error.message;
    } else {
        msg.style.color = "#4ade80";
        msg.textContent = "Check your email to confirm, then log in.";
    }
}

async function signIn() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const { error } = await supabaseClient.auth.signInWithPassword({ email, password });
    if (error) {
        document.getElementById("authMsg").textContent = error.message;
        return;
    }
    window.location.href = "/app";
}

async function signOut() {
    await supabaseClient.auth.signOut();
    window.location.href = "/";
}

// Returns the current access token, or redirects to /login if there isn't one.
async function requireSession() {
    const { data: { session } } = await supabaseClient.auth.getSession();
    if (!session) {
        window.location.href = "/";
        return null;
    }
    return session.access_token;
}
