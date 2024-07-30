$(function() {
    // disable these buttons on submit to prevent multiple submits
    $('.btn-submit').click(function(event) {
        $(this).addClass('disabled');
        $(this).attr('aria-disabled', 'true');
        var btn = new bootstrap.Button(this);
        btn.toggle();
    });
});
