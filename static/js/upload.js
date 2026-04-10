document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('documents-tbody');
    const fileUpload = document.getElementById('file-upload');
    const dropZone = document.getElementById('drop-zone');
    const progressCounter = document.getElementById('progress-counter');
    const progressBar = document.getElementById('progress-bar');
    const proceedBtn = document.getElementById('proceed-btn');
    const alertBox = document.getElementById('alert-box');
    const alertMsg = document.getElementById('alert-message');
    const uploadingSpinner = document.getElementById('uploading-spinner');

    let documentStatus = [];

    // Load initial data
    fetchDocuments();

    function fetchDocuments() {
        fetch('/api/documents')
            .then(res => res.json())
            .then(data => {
                documentStatus = data;
                renderTable();
                updateProgress();
            })
            .catch(err => {
                showAlert('Failed to load document status from server.', true);
                console.error(err);
            });
    }

    function renderTable() {
        tableBody.innerHTML = '';
        documentStatus.forEach(doc => {
            const row = document.createElement('tr');
            
            // Status Badge
            const statusClass = doc.status === 'Uploaded' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-yellow-100 text-yellow-800';
            
            // Confidence Badge
            let confClass = 'text-gray-500';
            let confText = '-';
            if (doc.status === 'Uploaded') {
                const confPercent = Math.round(doc.confidence_score * 100);
                confText = `${confPercent}%`;
                if (confPercent > 80) confClass = 'text-green-600 font-bold';
                else if (confPercent > 50) confClass = 'text-yellow-600 font-bold';
                else confClass = 'text-red-600 font-bold';
            }

            // File Size Formatting
            let fileSizeStr = '-';
            if (doc.file_size > 0) {
                fileSizeStr = (doc.file_size / (1024 * 1024)).toFixed(2) + ' MB';
            }

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">${doc.document_type}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">
                        ${doc.status}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-gray-500">
                    <div class="text-sm">${doc.file_type}</div>
                    <div class="text-xs">${fileSizeStr}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium ${doc.status === 'Uploaded' ? 'text-gray-900' : 'text-gray-400'}">
                        ${doc.ai_classification}
                    </div>
                    <div class="text-xs ${confClass}">Conf: ${confText}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-xs font-mono text-gray-500 overflow-hidden" style="max-width: 150px; text-overflow: ellipsis;" title="${doc.sha256_hash}">
                    ${doc.sha256_hash !== '-' ? doc.sha256_hash.substring(0, 16) + '...' : '-'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    ${doc.status === 'Uploaded' ? '<span class="text-green-600">&check; Success</span>' : '<span class="text-gray-400">Waiting...</span>'}
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    function updateProgress() {
        const uploadedCount = documentStatus.filter(d => d.status === 'Uploaded').length;
        const total = documentStatus.length;
        
        progressCounter.textContent = `${uploadedCount} / ${total}`;
        progressBar.style.width = `${(uploadedCount / total) * 100}%`;

        if (uploadedCount === total && total > 0) {
            proceedBtn.disabled = false;
        } else {
            proceedBtn.disabled = true;
        }
    }

    function showAlert(msg, isError = true) {
        alertMsg.textContent = msg;
        alertBox.classList.remove('hidden');
        if (isError) {
            alertBox.classList.remove('bg-green-50', 'border-green-500');
            alertMsg.classList.remove('text-green-700');
            alertBox.classList.add('bg-red-50', 'border-red-500');
            alertMsg.classList.add('text-red-700');
        } else {
            alertBox.classList.remove('bg-red-50', 'border-red-500');
            alertMsg.classList.remove('text-red-700');
            alertBox.classList.add('bg-green-50', 'border-green-500');
            alertMsg.classList.add('text-green-700');
        }
    }

    function hideAlert() {
        alertBox.classList.add('hidden');
    }

    // File Upload Handling
    fileUpload.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files);
        }
    });

    // Drag and Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('bg-blue-50', 'border-blue-500');
    });

    ['dragleave', 'dragend'].forEach(type => {
        dropZone.addEventListener(type, (e) => {
            e.preventDefault();
            dropZone.classList.remove('bg-blue-50', 'border-blue-500');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('bg-blue-50', 'border-blue-500');
        if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    });

    function handleFiles(files) {
        hideAlert();
        
        // Ensure only processing one at a time for simplicity/UI feedback, though you can loop
        const file = files[0];
        uploadingSpinner.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file', file);

        fetch('/api/upload', {
            method: 'POST',
            body: formData
        })
        .then(async res => {
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.error || 'Server error occurred during upload.');
            }
            return data;
        })
        .then(data => {
            uploadingSpinner.classList.add('hidden');
            showAlert(`Success: Document classified as ${data.document_type} (${Math.round(data.confidence * 100)}% Conf) - ${data.status}`, false);
            // Refresh table to get latest state
            fetchDocuments();
            fileUpload.value = ''; // Reset input
        })
        .catch(err => {
            uploadingSpinner.classList.add('hidden');
            showAlert(err.message, true);
            fileUpload.value = '';
        });
    }

    proceedBtn.addEventListener('click', () => {
        alert("Pipeline Stage 3 Placeholder: Proceeding to Financial Extraction...");
        // window.location.href = '/extraction';
    });
});
