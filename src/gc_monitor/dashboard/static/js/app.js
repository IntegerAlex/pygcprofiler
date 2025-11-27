// State
const state = {
    totalCollections: 0,
    totalDuration: 0,
    maxDuration: 0,
    collections: []
};

// Chart Setup
const ctx = document.getElementById('gcChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'scatter',
    data: {
        datasets: [
            {
                label: 'Gen 0',
                data: [],
                backgroundColor: '#4ade80',
                pointRadius: 4
            },
            {
                label: 'Gen 1',
                data: [],
                backgroundColor: '#facc15',
                pointRadius: 6
            },
            {
                label: 'Gen 2',
                data: [],
                backgroundColor: '#f87171',
                pointRadius: 8
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'second',
                    displayFormats: {
                        second: 'HH:mm:ss'
                    }
                },
                grid: {
                    color: '#334155'
                },
                ticks: {
                    color: '#94a3b8'
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Duration (ms)',
                    color: '#94a3b8'
                },
                grid: {
                    color: '#334155'
                },
                ticks: {
                    color: '#94a3b8'
                },
                beginAtZero: true
            }
        },
        plugins: {
            legend: {
                labels: {
                    color: '#f8fafc'
                }
            }
        }
    }
});

// Server-Sent Events Connection
let eventSource;

function connect() {
    console.log('Connecting to SSE endpoint...');
    eventSource = new EventSource('/events');

    eventSource.onopen = () => {
        console.log('SSE connection opened');
        const status = document.getElementById('connectionStatus');
        status.classList.add('connected');
        status.querySelector('span').textContent = 'Live';
    };

    eventSource.onerror = (error) => {
        console.error('SSE connection error:', error, 'readyState:', eventSource.readyState);
        // readyState: 0 = CONNECTING, 1 = OPEN, 2 = CLOSED
        if (eventSource.readyState === EventSource.CLOSED) {
            const status = document.getElementById('connectionStatus');
            status.classList.remove('connected');
            status.querySelector('span').textContent = 'Disconnected (Reconnecting...)';
            eventSource.close();
            setTimeout(connect, 2000);
        } else if (eventSource.readyState === EventSource.CONNECTING) {
            console.log('SSE reconnecting...');
        }
    };

    // Use onmessage (EventSource default handler)
    eventSource.onmessage = (event) => {
        console.log('Received SSE message:', event.data);
        try {
            const data = JSON.parse(event.data);
            console.log('Parsed data:', data);
            if (data.type === 'connected') {
                console.log('SSE connection confirmed');
                // Initial connection message, ignore
                return;
            }
            handleEvent(data);
        } catch (e) {
            console.error('Error parsing event data:', e, 'Raw data:', event.data);
        }
    };
}

function handleEvent(data) {
    console.log('Handling event:', data);
    // Update State
    state.totalCollections++;
    state.totalDuration += data.duration_ms;
    state.maxDuration = Math.max(state.maxDuration, data.duration_ms);

    // Update DOM
    document.getElementById('totalCollections').textContent = state.totalCollections;
    document.getElementById('avgDuration').textContent = (state.totalDuration / state.totalCollections).toFixed(2) + ' ms';
    document.getElementById('maxPause').textContent = state.maxDuration.toFixed(1) + ' ms';
    
    const genEl = document.getElementById('lastGen');
    genEl.textContent = `Gen ${data.generation}`;
    genEl.style.color = data.generation === 0 ? '#4ade80' : data.generation === 1 ? '#facc15' : '#f87171';

    // Update Chart
    const datasetIndex = data.generation; // 0, 1, or 2
    const point = {
        x: data.timestamp * 1000, // JS uses ms
        y: data.duration_ms
    };
    
    chart.data.datasets[datasetIndex].data.push(point);

    // Keep only last 5 minutes of data
    const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
    chart.data.datasets.forEach(dataset => {
        dataset.data = dataset.data.filter(p => p.x > fiveMinutesAgo);
    });
    
    chart.scales.x.min = fiveMinutesAgo;
    chart.scales.x.max = Date.now();
    
    chart.update();

    // Alert if pause > 50ms
    if (data.duration_ms > 50) {
        showAlert(`Long Pause: ${data.duration_ms.toFixed(1)}ms (Gen ${data.generation})`);
    }
}

function showAlert(msg) {
    const box = document.getElementById('alertBox');
    box.textContent = msg;
    box.classList.add('show');
    setTimeout(() => {
        box.classList.remove('show');
    }, 3000);
}

connect();

