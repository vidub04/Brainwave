const landing=document.getElementById("landing");

const interview=document.getElementById("interview");

document.getElementById("startBtn").addEventListener("click",()=>{

    landing.style.display="none";

    interview.style.display="block";

});

let seconds=0;

setInterval(()=>{

    seconds++;

    const min=Math.floor(seconds/60);

    const sec=seconds%60;

    document.getElementById("timer").innerText=

    `${String(min).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;

},1000);


async function sendPrompt(){

    const prompt=document.getElementById("prompt");

    const chatBox=document.getElementById("chatBox");

    const text=prompt.value.trim();

    if(text==="") return;

    const formatted = marked.parse(data.response);

    chatBox.innerHTML += `
    <div class="message bot">
        <div class="avatar">🤖</div>
        <div class="bubble">${formatted}</div>
    </div>
    `;

    prompt.value="";

    chatBox.scrollTop=chatBox.scrollHeight;

    const res=await fetch("/generate",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({
            prompt:text
        })

    });

    const data=await res.json();

    chatBox.innerHTML+=`
    <div class="message bot">
        <div class="avatar">🤖</div>
        <div class="bubble">${data.response}</div>
    </div>
    `;

    chatBox.scrollTop=chatBox.scrollHeight;

}