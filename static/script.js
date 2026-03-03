function sendMessage() {
    const input = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
    const text = input.value.trim();

    if (!text) return;

    // 1. Add User Message
    chatWindow.innerHTML += `<div class="message user">${text}</div>`;
    
    // 2. Simulate Agentic Workflow
    processAgenticLogic(text);

    input.value = '';
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function processAgenticLogic(query) {
    const status = document.getElementById('agent-status');
    const toolName = document.getElementById('tool-name');
    const jsonDisplay = document.getElementById('json-display');
    const logList = document.getElementById('log-list');

    // Reset UI for new action
    status.innerText = "PROCESSING...";
    logList.innerHTML = "<li>Analyzing user intent...</li>";

    setTimeout(() => {
        if (query.toLowerCase().includes("schedule") || query.toLowerCase().includes("meeting")) {
            // Trigger Meeting Tool
            toolName.innerText = "Calendar_Agent_V1";
            status.innerText = "ACTION TRIGGERED";
            
            const jsonAction = {
                action: "schedule_meeting",
                parameters: {
                    participant: "HR Manager",
                    subject: "Internal Policy Review",
                    time_slot: "2026-01-20T10:00:00Z"
                },
                requires_confirmation: true
            };
            
            jsonDisplay.innerText = JSON.stringify(jsonAction, null, 4);
            logList.innerHTML += "<li>Intent: Schedule Meeting detected.</li>";
            logList.innerHTML += "<li>Mapping parameters to Function: schedule_meeting().</li>";
            logList.innerHTML += "<li><strong>Success:</strong> Valid JSON generated for mock execution.</li>";
        } else {
            // Default RAG Retrieval
            status.innerText = "IDLE";
            toolName.innerText = "Knowledge_Retrieval";
            jsonDisplay.innerText = '{ "mode": "rag_search", "query_embedding": "success" }';
            
            const chatWindow = document.getElementById('chat-window');
            chatWindow.innerHTML += `<div class="message system">Based on the HCLTech Annual Report (Page 45), the strategic focus is on Digital Transformation and AI. [Source: Page 45]</div>`;
        }
    }, 1000);
}

function setDomain(domain) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    console.log("Domain switched to: " + domain);
}