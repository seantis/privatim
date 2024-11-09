document.addEventListener('DOMContentLoaded', function () {
    initializePopoversAndTooltips();
    listenForChangesInAttendees();
    handleProfilePicFormSubmission();
    setupCommentAnswerField();
    addEditorForCommentsEdit();
    makeConsultationsInActivitiesClickable();
    setupAgendaItemGlobalToggle();
    setupDeleteModalListeners();
    autoHideSuccessMessages();
    addTestSystemBadge();
    fixCSSonProfilePage();
});


function setupDeleteModalListeners() {
    var active_popover = null;
    var popover_timeout = null;

    // Update the modal dismissal logic
    $('#delete-xhr').on('hidden.bs.modal', function (e) {
        // Ensure the modal backdrop is removed
        $('.modal-backdrop').remove();
        $('body').removeClass('modal-open');
        $('body').css('padding-right', '');
    });

    // Update the cancel button click handler
    $('#delete-xhr .btn-secondary').on('click', function (event) {
        event.preventDefault();
        var modal = bootstrap.Modal.getInstance(document.getElementById('delete-xhr'));
        if (modal) {
            modal.hide();
        }
    });

    const deleteModal = document.getElementById('delete-xhr');

    if (!deleteModal) {
        return;
    }

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
                        bootstrap.Modal.getInstance(deleteModal).hide()
                    }
                    if (response.redirect_url) {
                        window.location.href = response.redirect_url;
                    }
                } else {
                    // Handle error
                    console.error('Deletion failed:', xhr.statusText);
                    console.error(xhr.status);
                }
            }
        };

        xhr.send();
    });

}


function makeConsultationsInActivitiesClickable() {
    // Ensure that the entire consultation card is clickable, even if clicked on a link within it,
    // still redirect to the consultation page.

    if (window.location.href.includes('/consultations')) {
        const cards = document.querySelectorAll('.consultation-card');
        cards.forEach(card => {
            const consultationUrl = card.dataset.href;

            // Find all links within the card
            const links = card.querySelectorAll('a');

            // Modify behavior for all links within the card
            links.forEach(link => {
                link.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    window.location.href = consultationUrl;
                });

                // Remove target attribute to prevent opening in new tab
                link.removeAttribute('target');

                // Optional: Change cursor to pointer to indicate clickability
                link.style.cursor = 'pointer';
            });

            // Make the entire card clickable
            card.addEventListener('click', function (e) {
                if (e.target.tagName.toLowerCase() !== 'a') {
                    e.preventDefault();
                    window.location.href = consultationUrl;
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

/**
 * Enables inline editing for comments.
 *
 * Attaches click listeners to elements with the `.edit-comment-link` class. When clicked, replaces the comment's content
 * with a textarea for editing.
 * Assumes `data-comment-id` attributes on edit links and IDs of format `#comment-content-{commentId}` for comments.
 */
function addEditorForCommentsEdit() {
    // For each comment, attach a listener for edit button to swap out the <p> tag with an editor to allow inline editing of comment.
    document.querySelectorAll('.edit-comment-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const commentId = this.dataset.commentId;
            const commentContentElement = document.querySelector(`#comment-content-${commentId}`);
            var originalContent = commentContentElement.textContent.trim();
            // Escape HTML
            originalContent = $('<div>').text(originalContent).html();

            commentContentElement.innerHTML = `
        <textarea class="form-control edit-comment-textarea" id="edit-textarea-${commentId}">${originalContent}</textarea>
        <div class="d-flex justify-content-end mt-2 pt-1">
            <button class="btn btn-secondary mt-2 cancel-edit-btn" data-comment-id="${commentId}">Abbrechen</button>
            <button class="btn btn-primary mt-2 save-edit-btn" data-comment-id="${commentId}" style="margin-left: 1rem;">Speichern</button>
        </div>
      `;

            document.querySelector(`#comment-content-${commentId} .save-edit-btn`).addEventListener('click', function () {
                const editedContent = document.querySelector(`#edit-textarea-${commentId}`).value;
                saveCommentEdit(commentId, editedContent);
            });

            document.querySelector(`#comment-content-${commentId} .cancel-edit-btn`).addEventListener('click', function () {
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

    xhr.onreadystatechange = function () {
        if (xhr.readyState === XMLHttpRequest.DONE) {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success) {
                        const content = $('<div>').text(response.content).html();
                        document.querySelector(`#comment-content-${commentId}`).innerHTML = content;
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

    xhr.onerror = function () {
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

// Expand / collapse all Agenda Items
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


function listenForChangesInAttendees() {
    // Synchronize Attendees and Attendance fields
    // Dynamically update the Attendance field when Attendees are added
    // This ensures consistency before form submission
    const tomSelectWrapper = document.querySelector('.ts-wrapper');
    const attendanceList = document.querySelector('.attendance-list');

    if (!tomSelectWrapper || !attendanceList) {
        return;
    }

    function addAttendee(userId, name) {
        // need to make sure that the × character is not part of the inserted name!
        const existingAttendee = document.querySelector(`input[value="${userId}"]`);
        // prevent adding duplicates
        if (existingAttendee) {
            return;
        }
        const newIndex = attendanceList.children.length - 1; // -1 due to header
        const newRow = document.createElement('div');
        newRow.className = 'attendance-row d-flex justify-content-between align-items-center mb-2';
        newRow.innerHTML = `
        <input class="form-control hidden no-white-background" id="attendance-${newIndex}-user_id" name="attendance-${newIndex}-user_id" type="hidden" value="${userId}">
        <span class="attendee-name col-6"><input class="form-control-plaintext" disabled="disabled" id="attendance-${newIndex}-fullname" name="attendance-${newIndex}-fullname" type="text" value="${name}"></span>
        <span class="attendee-status col-3 text-center"><input class="form-check-input" id="attendance-${newIndex}-status" name="attendance-${newIndex}-status" type="checkbox" value="y" checked></span>
        <span class="attendee-remove col-3 text-center">
            <input class="form-check-input text-danger" id="attendance-${newIndex}-remove" name="attendance-${newIndex}-remove" type="checkbox" value="y">
        </span>
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
                        addAttendee(userId, name.replace('×', ''));
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

    // Remove attendance rows with value="", inappropriately returned by the backend in case of form errors.
    // I can't find an elegant way to prevent this on the backend side.
    // This is reciprocal with MeetingForm.process()
    const attendanceRows = document.querySelectorAll('.attendance-row');
    attendanceRows.forEach(row => {
        const fullnameInput = row.querySelector('input[id^="attendance-"][id$="-fullname"]');
        if (fullnameInput && fullnameInput.value.trim() === '') {
            row.remove();
        }
    });
}


// Makes only sense to show upload field if 'replace' is selected for edit file form. (UploadMultipleFilesWithORMSupport)
$(function () {
    $('.upload-field').each(function (index, element) {
        var upload = $(element).find('input[type="file"]');
        $(element).find('input[type="radio"]').change(function () {
            if (this.value === 'keep') {
                upload.prop('disabled', true);
                upload.prop('required', false);
            } else if (this.value === 'replace') {
                upload.prop('disabled', false);
                upload.prop('required', true);
            }
        }).filter(':checked').change();
    });
});


// Vanish the flash message if positive after N seconds automatically.
function autoHideSuccessMessages() {
    const delay = 3000;
    const successAlerts = document.querySelectorAll('.alert-success');

    successAlerts.forEach((alert) => {
        setTimeout(() => {
            // Start the fade out
            alert.classList.add('hiding');

            // Listen for the end of the transition
            alert.addEventListener('transitionend', function handleTransitionEnd(event) {
                if (event.propertyName === 'opacity') {
                    // Remove the event listener
                    alert.removeEventListener('transitionend', handleTransitionEnd);

                    // Find and remove the container
                    let container = alert.closest('.container');
                    if (container) {
                        // Check if this container only contained this alert
                        if (container.children.length === 1 && container.children[0] === alert) {
                            // If so, remove the entire container
                            container.remove();
                        } else {
                            // Otherwise, just remove the alert
                            alert.remove();
                        }
                    } else {
                        // If no container found, just remove the alert
                        alert.remove();
                    }

                    // Check if we need to remove the p-4 div
                    let p4Div = document.querySelector('.p-4:empty');
                    if (p4Div) {
                        p4Div.remove();
                    }
                }
            });
        }, delay);
    });
}

function addTestSystemBadge() {
    const testBadge = document.getElementById('testBadge');
    if (window.location.href.includes('test')) {
        testBadge.style.display = 'inline-block';
    }
}


function fixCSSonProfilePage() {
    // todo: this can be removed soon
    const currentUrl = window.location.href;
    const profilePath = '/profile';
    const reloadKey = 'profilePageReloaded';

    if (currentUrl.includes(profilePath) && !localStorage.getItem(reloadKey)) {
        localStorage.setItem(reloadKey, 'true');

        // Invalidate the cache for CSS by appending a random query parameter
        const cssLinks = document.querySelectorAll('link[rel="stylesheet"]');
        cssLinks.forEach(link => {
            const href = link.href;
            link.href = `${href}?_=${new Date().getTime()}`;
        });

        // Perform a hard reload
        window.location.reload(true);
    }
}
