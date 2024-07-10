document.addEventListener('DOMContentLoaded', (event) => {

    document.querySelectorAll('.searchable-select').forEach((el)=>{
        console.log('setting up tomselect')
        let settings = {};
        new TomSelect(el,settings);
    });
});
