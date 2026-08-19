/*new files 
const config = await fetch("/config").then(res => res.json());

const SUPABASE_URL = config.supabase_url;
const SUPABASE_ANON_KEY = config.supabase_anon_key;

*/

let supabaseClient=null

async function create_client() {

    const res = await fetch("/config");
    const data = await res.json();

    supabaseClient = window.supabase.createClient(
        data.supabase_url,
        data.supabase_anon_key
    );

    console.log("Supabase initialized");

  
}


/*const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);*/

const supabaseReady=create_client();

async function signUp() {

    if (!supabaseReady) {
        document.getElementById("authMsg").textContent =
            "Please wait, authentication is initializing...";
        return;
    }
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
