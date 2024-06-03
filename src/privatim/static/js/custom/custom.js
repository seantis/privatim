document.addEventListener('DOMContentLoaded', function () {
    initializePopoversAndTooltips();
    handleProfilePicFormSubmission();
});

function handleProfilePicFormSubmission() {

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
