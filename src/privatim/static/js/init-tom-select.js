document.addEventListener('DOMContentLoaded', (event) => {

    document.querySelectorAll('.searchable-select').forEach((el)=>{
        let settings = {};
        new TomSelect(el,settings);
    });
});
