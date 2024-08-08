document.addEventListener('DOMContentLoaded', function () {
    initializePopoversAndTooltips();
    handleProfilePicFormSubmission();
    setupCommentAnswerField();
    setupCommentEditFlow();
    makeConsultationsClickable();


});

function makeConsultationsClickable() {
    // The whole consultation card was previously wrapped in a link before. This worked until we started rendering
    // user-generated links (as html from the editor) in the description. Nesting Link is not allowed by HTML standard.
    if (window.location.href.includes('/consultations')) {
        const cards = document.querySelectorAll('.consultation-card');
        cards.forEach(card => {
            card.addEventListener('click', function (e) {
                if (e.target.tagName !== 'A') {
                    window.location.href = this.dataset.href;
                }
            });
        });
    }
}

function handleProfilePicFormSubmission() {
    // Manually submit the form in profile picture view.

    // We have to use js here which is a bit unfortunate, but placing the form inside a dropdown menu creates a lot of
    // styling problems. So we keep the form outside.
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const formInput = document.getElementById('fileUploadInput');
    const uploadPhotoLink = document.getElementById('uploadPhotoLink');
    if (!(fileInput && uploadForm && formInput && uploadPhotoLink)) {
        return;
    }
    uploadPhotoLink.addEventListener('click', function (event) {
        event.preventDefault();
        fileInput.click();
    });
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) {
            formInput.files = fileInput.files;
            uploadForm.submit();
        }
    });

    document.getElementById('deletePhotoLink').addEventListener('click', function (event) {
        event.preventDefault();

        const deleteUrl = this.getAttribute('href');
        const csrfToken = document.querySelector('input[name="csrf_token"]').value;

        const xhr = new XMLHttpRequest();
        xhr.open('DELETE', deleteUrl, true);
        xhr.setRequestHeader('X-CSRF-Token', csrfToken);
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status >= 200 && xhr.status < 300) {
                    const response = JSON.parse(xhr.responseText);
                    if (response.redirect_url) {
                        window.location.href = response.redirect_url;
                    }
                }
            }
        };
        xhr.send();
    });
}


function initializePopoversAndTooltips() {
    // https://getbootstrap.com/docs/5.0/components/popovers/#example-enable-popovers-everywhere
    const triggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"], [data-bs-toggle="tooltip"]'));
    triggerList.forEach(function (triggerEl) {
        if (triggerEl.getAttribute('data-bs-toggle') === 'popover') {
            new bootstrap.Popover(triggerEl);
        } else if (triggerEl.getAttribute('data-bs-toggle') === 'tooltip') {
            new bootstrap.Tooltip(triggerEl);
        }
    });
}


function setupCommentEditFlow() {
    document.querySelectorAll('.edit-comment-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const commentId = this.dataset.commentId;
            const commentContentElement = document.querySelector(`#comment-content-${commentId}`);
            const originalContent = commentContentElement.textContent.trim();

            // Replace content with textarea
            commentContentElement.innerHTML = `
        <textarea class="form-control edit-comment-textarea" id="edit-textarea-${commentId}">${originalContent}</textarea>
        <button class="btn btn-primary mt-2 save-edit-btn" data-comment-id="${commentId}">Save</button>
        <button class="btn btn-secondary mt-2 cancel-edit-btn" data-comment-id="${commentId}">Cancel</button>
      `;
            // Setup save button
            document.querySelector(`#comment-content-${commentId} .save-edit-btn`).addEventListener('click', function () {

                const editedContent = document.querySelector(`#edit-textarea-${commentId}`).value;
                const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

                fetch(`/comments/${commentId}/edit`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': csrfToken
                    },
                    body: JSON.stringify({content: editedContent})
                })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Network response was not ok');
                        }
                        return response.json();
                    })
                    .then(data => {
                        if (data.success) {
                            document.querySelector(`#comment-content-${commentId}`).innerHTML = editedContent;
                        } else {
                            alert('Error updating comment: ' + data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Error updating comment');
                    });
            });

            // Setup cancel button
            document.querySelector(`#comment-content-${commentId} .cancel-edit-btn`).addEventListener('click', function () {
                commentContentElement.innerHTML = originalContent;
            });
        });
    });
}


function setupCommentAnswerField() {
    // Makes the answer comment form appear.
    let replys = document.querySelectorAll('.comment-answer-form-container');
    let buttons = document.querySelectorAll('.comment-answer-button');
    for (let i = 0; i < buttons.length; i++) {
        let hiddenCommentForm = replys[i];
        buttons[i].addEventListener('click', () => {
            hiddenCommentForm.classList.add('show');
            setTimeout(() => {
                hiddenCommentForm.querySelector('textarea').focus();
            }, 200);
        });

    }
}


(function () {
    document.addEventListener('DOMContentLoaded', function () {
        const tomSelectWrapper = document.querySelector('.ts-wrapper');
        const attendanceList = document.querySelector('.attendance-list');

        if (!tomSelectWrapper || !attendanceList) {
            return;
        }

        function addAttendee(userId, name) {
            const existingAttendee = document.querySelector(`input[value="${userId}"]`);
            if (existingAttendee) {
                return;
            }

            const newIndex = attendanceList.children.length - 1; // -1 for header
            const newRow = document.createElement('div');
            newRow.className = 'attendance-row';
            newRow.innerHTML = `
            <input class="hidden no-white-background" id="attendance-${newIndex}-user_id" name="attendance-${newIndex}-user_id" type="hidden" value="${userId}">
            <span class="attendee-name"><input class="form-control no-white-background" disabled="disabled" id="attendance-${newIndex}-fullname" name="attendance-${newIndex}-fullname" type="text" value="${name}"></span>
            <span class="attendee-status"><input checked class="no-white-background" id="attendance-${newIndex}-status" name="attendance-${newIndex}-status" type="checkbox" value="y"></span>
        `;
            attendanceList.appendChild(newRow);
        }

        function removeAttendee(userId) {
            const rowToRemove = document.querySelector(`input[value="${userId}"]`).closest('.attendance-row');
            if (rowToRemove) {
                rowToRemove.remove();
            }
        }

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains('item')) {
                            const userId = node.getAttribute('data-value');
                            const name = node.textContent;
                            addAttendee(userId, name);
                        }
                    });
                    mutation.removedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains('item')) {
                            const userId = node.getAttribute('data-value');
                            removeAttendee(userId);
                        }
                    });
                }
            });
        });

        observer.observe(tomSelectWrapper, {childList: true, subtree: true});
    });
})(); // IIFE ends here
