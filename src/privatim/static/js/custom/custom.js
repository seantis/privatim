document.addEventListener('DOMContentLoaded', function () {
    initializePopoversAndTooltips();
    handleProfilePicFormSubmission();
    setupCommentAnswerField();
    addEditorForCommentsEdit();
    makeConsultationsInActivitiesClickable();
    setupAgendaItemGlobalToggle();
    setupDeleteModalForPersonInPeople();
    autoHideSuccessMesssages('.alert-success');
});


function setupDeleteModalForPersonInPeople() {
    if (window.location.pathname !== '/people') {
       return;
    }

    const deleteModal = document.getElementById('delete-xhr');
    const deleteButtons = document.querySelectorAll('[data-bs-target="#delete-xhr"]');
    const deleteModalItemTitle = document.getElementById('delete-xhr-item-title');
    const deleteConfirmButton = deleteModal.querySelector('.btn-danger');

    deleteButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            event.preventDefault();
            const itemTitle = button.getAttribute('data-item-title');
            const deleteUrl = button.getAttribute('href');

            if (deleteModalItemTitle) {
                deleteModalItemTitle.textContent = itemTitle;
            }

            if (deleteConfirmButton) {
                deleteConfirmButton.href = deleteUrl;
            }

            const modal = new bootstrap.Modal(deleteModal);
            modal.show();
        });
    });

    deleteConfirmButton.addEventListener('click', (event) => {
        event.preventDefault();
        const csrfToken = document.querySelector('input[name="csrf_token"]').value;
        const deleteUrl = deleteConfirmButton.href;
        console.log(deleteUrl);

        const xhr = new XMLHttpRequest();
        xhr.open('DELETE', deleteUrl, true);
        xhr.setRequestHeader('X-CSRF-Token', csrfToken);
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status >= 200 && xhr.status < 300) {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success) {
                        // Handle successful deletion
                        const deletedItemId = deleteUrl.split('/').pop();
                        const deletedItem = document.getElementById(deletedItemId);
                        if (deletedItem) {
                            deletedItem.remove();
                        }
                        // Close the modal
                        bootstrap.Modal.getInstance(deleteModal).hide()
                    }
                    if (response.redirect_url) {
                        window.location.href = response.redirect_url;
                    }
                } else {
                    // Handle error
                    console.error('Deletion failed:', xhr.statusText);
                }
            }
        };

        xhr.send();
    });

}

function makeConsultationsInActivitiesClickable() {
    // Nesting links is not allowed by HTML standards. The 'Consultation' activity should still be clickable,
    // even if it contains a link within the text. This workaround ensures all links function properly.
    if (window.location.href.includes('/consultations')) {
        const cards = document.querySelectorAll('.consultation-card');
        cards.forEach(card => {
            card.addEventListener('click', function (e) {
                // Safeguard for links inside it (content created by user)
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

function addEditorForCommentsEdit() {
    document.querySelectorAll('.edit-comment-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.dataset.commentId;
            const commentContentElement = document.querySelector(`#comment-content-${commentId}`);
            const originalContent = commentContentElement.textContent.trim();

            commentContentElement.innerHTML = `
        <textarea class="form-control edit-comment-textarea" id="edit-textarea-${commentId}">${originalContent}</textarea>
        <div class="d-flex justify-content-end mt-2 pt-1">
            <button class="btn btn-secondary mt-2 cancel-edit-btn" data-comment-id="${commentId}">Abbrechen</button>
            <button class="btn btn-primary mt-2 save-edit-btn" data-comment-id="${commentId}" style="margin-left: 1rem;">Speichern</button>
        </div>
      `;

            document.querySelector(`#comment-content-${commentId} .save-edit-btn`).addEventListener('click', function() {
                const editedContent = document.querySelector(`#edit-textarea-${commentId}`).value;
                saveCommentEdit(commentId, editedContent);
            });

            document.querySelector(`#comment-content-${commentId} .cancel-edit-btn`).addEventListener('click', function() {
                commentContentElement.innerHTML = originalContent;
            });
        });
    });
}

function saveCommentEdit(commentId, editedContent) {
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;

    const formData = new FormData();
    formData.append('content', editedContent);
    formData.append('csrf_token', csrfToken);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/comments/${commentId}/edit`, true);
    xhr.setRequestHeader('X-CSRF-Token', csrfToken);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    xhr.onreadystatechange = function() {
        if (xhr.readyState === XMLHttpRequest.DONE) {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success) {
                        document.querySelector(`#comment-content-${commentId}`).innerHTML = response.content;
                    } else {
                        console.error('Error updating comment:', response.message || 'Unknown error');
                    }
                } catch (error) {
                    console.error('Error parsing JSON:', error);
                }
            } else {
                console.error('HTTP error:', xhr.status, xhr.statusText);
            }
        }
    };

    xhr.onerror = function() {
        console.error('Network error occurred while updating comment');
    };

    xhr.send(formData);
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

function setupAgendaItemGlobalToggle() {
    if (!window.location.href.includes('/meeting')) {
       return;
    }

    const toggleBtn = document.getElementById('toggleAllItems');
    if (!toggleBtn) {
        return;
    }
    const accordionItems = document.querySelectorAll('.accordion-collapse');
    let isExpanded = false;

    function toggleAll() {
        isExpanded = !isExpanded;
        accordionItems.forEach(item => {
            const bsCollapse = new bootstrap.Collapse(item, {
                toggle: false
            });
            if (isExpanded) {
                bsCollapse.show();
            } else {
                bsCollapse.hide();
            }
        });

        // Update button text and icon
        const btnText = toggleBtn.querySelector('span');
        const btnIcon = toggleBtn.querySelector('i');
        if (isExpanded) {
            btnText.textContent = toggleBtn.dataset.collapseText;
            btnIcon.classList.replace('fa-caret-down', 'fa-caret-up');
        } else {
            btnText.textContent = toggleBtn.dataset.expandText;
            btnIcon.classList.replace('fa-caret-up', 'fa-caret-down');
        }
    }

    toggleBtn.addEventListener('click', toggleAll);

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


// Makes only sense to show upload field if 'replace' is selected for edit file form. (UploadMultipleFilesWithORMSupport)
$(function() {
    $('.upload-field').each(function(index, element) {
        var upload = $(element).find('input[type="file"]');
        $(element).find('input[type="radio"]').change(function() {
            if(this.value === 'keep') {
                upload.prop('disabled', true);
                upload.prop('required', false);
            } else if(this.value === 'replace') {
                upload.prop('disabled', false);
                upload.prop('required', true);
            }
        }).filter(':checked').change();
    });
});


function autoHideSuccessMesssages(alertSelector, delay = 4000) {
    const alertElement = document.querySelector('main.main-content .container .alert-success');

    if (alertElement) {
        setTimeout(() => {
            alertElement.classList.remove('show');
            alertElement.addEventListener('transitionend', () => {
                // Remove the entire alert container to clean up the empty space
                const alertContainer = alertElement.closest('.container');
                if (alertContainer) {
                    alertContainer.remove();
                }
            });
        }, delay);
    }
}
