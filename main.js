import * as XLSX from 'xlsx';

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const statusSection = document.getElementById('status-section');
const resultsSection = document.getElementById('results-section');
const currentTaskLabel = document.getElementById('current-task');
const progressPercent = document.getElementById('progress-percent');
const progressFill = document.getElementById('progress-fill');
const pageStatus = document.getElementById('page-status');
const outputText = document.getElementById('output-text');
const copyBtn = document.getElementById('copy-btn');
const downloadBtn = document.getElementById('download-btn');
const startPageInput = document.getElementById('start-page');
const endPageInput = document.getElementById('end-page');

let isProcessing = false;
let pageData = [];
let originalFileName = 'extracted_data';

// Event Listeners
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFile(e.target.files[0]);
    }
});

async function handleFile(file) {
    const isImage = file.type.startsWith('image/');
    const isPdf = file.type === 'application/pdf';
    if (!isPdf && !isImage) {
        alert('Please upload a PDF or image file.');
        return;
    }

    if (isProcessing) return;
    isProcessing = true;

    // Save filename (remove extension)
    originalFileName = file.name.replace(/\.[^/.]+$/, "");

    // Reset UI
    statusSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    outputText.value = '';
    pageData = [];
    updateProgress(0, 'Uploading to Backend...');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('http://localhost:5000/ocr', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Backend processing failed');
        }

        updateProgress(50, 'Processing OCR...');
        const result = await response.json();
        
        if (result.error) {
            throw new Error(result.error);
        }

        pageData = result.voters;
        outputText.value = result.raw_text;
        
        updateProgress(100, 'Completed!');
        statusSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');

    } catch (error) {
        console.error('Processing error:', error);
        alert('An error occurred: ' + error.message);
        statusSection.classList.add('hidden');
    } finally {
        isProcessing = false;
    }
}

function updateProgress(percent, task) {
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${Math.round(percent)}%`;
    currentTaskLabel.textContent = task;
}

// Actions
copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(outputText.value);
    const originalText = copyBtn.textContent;
    copyBtn.textContent = 'Copied!';
    setTimeout(() => copyBtn.textContent = originalText, 2000);
});

downloadBtn.addEventListener('click', () => {
    const blob = new Blob([outputText.value], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${originalFileName}_text.txt`;
    a.click();
    URL.revokeObjectURL(url);
});
