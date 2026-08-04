async function sendPrompt() {

            const prompt = document.getElementById("prompt").value;

            const res = await fetch("/generate", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    prompt: prompt
                })

            });

            const data = await res.json();

            document.getElementById("response").innerText = data.response;

}