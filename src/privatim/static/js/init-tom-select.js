document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.searchable-select').forEach((el) => {
        let settings = {};
        new TomSelect(el, settings);
    });
});
