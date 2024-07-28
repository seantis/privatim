document.addEventListener('DOMContentLoaded', function () {
    initializePopoversAndTooltips();
    handleProfilePicFormSubmission();
    setupCommentAnswerField();

    if (window.location.href.includes('consultations/edit')) {
        document.querySelectorAll('.upload-widget.without-data').forEach(el => {
            el.style.display = 'none';
        });
    }
});

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
// Add users to table if added in the Multiple Select field
    document.addEventListener('DOMContentLoaded', function () {
        const tomSelectWrapper = document.querySelector('.ts-wrapper');
        const attendanceList = document.querySelector('.attendance-list');

        if (!tomSelectWrapper || !attendanceList) {
            console.error('Required elements not found. Please check your selectors.');
            return;
        }

        // Function to add a new attendee to the attendance list
        function addAttendee(userId, name) {
            const existingAttendee = document.querySelector(`#attendance-${userId}`);
            if (existingAttendee) {
                return;
            }

            if (!document.querySelector(`#attendance-${userId}`)) {
                const newRow = document.createElement('div');
                newRow.className = 'attendance-row';
                newRow.id = `attendance-${userId}`;
                newRow.innerHTML = `
                <input class="form-control hidden no-white-background" id="attendance-${userId}-user_id" name="attendance-${userId}-user_id" type="hidden" value="${userId}">
                <span class="attendee-name"><input class="form-control no-white-background" disabled="disabled" id="attendance-${userId}-fullname" name="attendance-${userId}-fullname" type="text" value="${name}"></span>
                <span class="attendee-status"><input checked class="no-white-background" id="attendance-${userId}-status" name="attendance-${userId}-status" type="checkbox" value="y"></span>
            `;
                attendanceList.appendChild(newRow);
                console.log('Attendee added:', {userId, name});
            }
        }

        // Function to remove an attendee from the attendance list
        function removeAttendee(userId) {
            const rowToRemove = document.querySelector(`#attendance-${userId}`);
            if (rowToRemove) {
                rowToRemove.remove();
                console.log('Attendee removed:', userId);
            }
        }

        // Set up the Mutation Observer
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

        // Start observing the TomSelect wrapper
        observer.observe(tomSelectWrapper, {childList: true, subtree: true});
    });
})(); // IIFE ends here
