const socket = new WebSocket(`ws://${window.location.host}/ws/audit`);
const output = document.getElementById('output');
const riskFeed = document.getElementById('risk-feed');

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'text') {
        appendTerminalMessage(data.content);
        // Logic to "Extract" risks from text and put them in the sidebar
        if (data.content.toLowerCase().includes('critical') || data.content.toLowerCase().includes('risk')) {
            updateRiskFeed(data.content);
        }
    } else if (data.type === 'tool') {
        appendToolBadge(data.content);
    }
};

function appendTerminalMessage(content) {
    const div = document.createElement('div');
    div.className = 'text-gray-300 leading-relaxed opacity-0 animate-fade-in';
    div.style.animation = 'fadeIn 0.5s forwards';
    div.innerHTML = `<span class="text-cyan-500 mr-2">●</span> ${content}`;
    output.appendChild(div);
    output.scrollTop = output.scrollHeight;
}

function appendToolBadge(toolName) {
    const div = document.createElement('div');
    div.className = 'flex items-center gap-2 bg-cyan-900/20 border border-cyan-500/30 text-cyan-400 px-3 py-1 rounded text-[10px] w-max';
    div.innerHTML = `<i class="fa-solid fa-gear animate-spin"></i> SYSTEM CALL: ${toolName}`;
    output.appendChild(div);
}

function updateRiskFeed(finding) {
    const div = document.createElement('div');
    div.className = 'bg-red-500/10 border-l-2 border-red-500 p-2 text-[11px] text-red-200';
    div.innerHTML = `<strong>THREAT DETECTED:</strong> ${finding.substring(0, 50)}...`;
    riskFeed.prepend(div);
}

function startAudit() {
    const input = document.getElementById('userInput');
    if (!input.value) return;
    socket.send(input.value);
    input.value = "";
}