document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('transcribeForm');
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const fileNameDisplay = document.getElementById('fileName');
    const submitBtn = document.getElementById('submitBtn');
    const spinner = document.getElementById('spinner');
    const statusMessage = document.getElementById('statusMessage');

    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        dropZone.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }

    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    fileInput.addEventListener('change', function () {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            fileInput.files = files;
            fileNameDisplay.textContent = files[0].name;
        }
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Handle Swiss German selection
        const modelSelect = document.getElementById('model');
        const langSelect = document.getElementById('lang');
        const SWISS_GERMAN_MODEL = 'nebi/whisper-large-v3-turbo-swiss-german-ct2-int8';

        langSelect.addEventListener('change', () => {
            if (langSelect.value === 'gsw') {
                modelSelect.value = SWISS_GERMAN_MODEL;
                showStatus('Swiss German model auto-selected.', 'normal');
            }
        });

        modelSelect.addEventListener('change', () => {
            // Optional logic if needed when model changes manually
        });


        if (!fileInput.files.length) {
            showStatus('Please select a file first.', 'error');
            return;
        }

        setLoading(true);
        showStatus('Transcribing...', 'normal');

        // Reset progress
        const progressContainer = document.getElementById('progressContainer');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressText.textContent = '0%';

        const formData = new FormData(form);

        // Map Swiss German (gsw) to German (de) for the backend/model
        if (formData.get('lang') === 'gsw') {
            formData.set('lang', 'de');
        }

        try {
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.trim()) continue;

                    try {
                        const data = JSON.parse(line);

                        if (data.type === 'progress') {
                            const percent = Math.round(data.value * 100);
                            progressBar.style.width = `${percent}%`;
                            progressText.textContent = `${percent}%`;
                        } else if (data.type === 'status') {
                            showStatus(data.message, 'normal');
                        } else if (data.type === 'complete') {
                            progressBar.style.width = '100%';
                            progressText.textContent = '100%';
                            showStatus('Transcription complete! Download started.', 'success');

                            // Trigger download
                            const a = document.createElement('a');
                            a.style.display = 'none';
                            a.href = data.url;
                            a.download = data.url.split('/').pop();
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                        } else if (data.type === 'error') {
                            showStatus(`Error: ${data.message}`, 'error');
                        }
                    } catch (e) {
                        console.error('Error parsing JSON:', e);
                    }
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showStatus('An unexpected error occurred.', 'error');
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        spinner.style.display = isLoading ? 'block' : 'none';
    }

    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = 'status-message';
        if (type === 'success') statusMessage.classList.add('status-success');
        if (type === 'error') statusMessage.classList.add('status-error');
    }
});
