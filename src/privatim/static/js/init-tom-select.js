document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.searchable-select').forEach((el) => {
        let settings = {'maxOptions': 1000};
        new TomSelect(el, settings);
    });
});
