async function sendPrompt(){

    const prompt = document.getElementById("prompt");

    const chatBox = document.getElementById("chatBox");

    const text = prompt.value.trim();

    if(text==="") return;

    chatBox.innerHTML += `
    <div class="message user">
        <div class="avatar">😊</div>
        <div class="bubble">${text}</div>
    </div>
    `;

    prompt.value="";

    const res = await fetch("/generate",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            prompt:text
        })
    });

    const data = await res.json();

    chatBox.innerHTML += `
    <div class="message bot">
        <div class="avatar">🤖</div>
        <div class="bubble">${data.response}</div>
    </div>
    `;

    chatBox.scrollTop = chatBox.scrollHeight;
}