document.querySelectorAll('.searchable-select').forEach((el)=>{

    console.log('el:');
    console.log(el);
	let settings = {};
 	new TomSelect(el,settings);
});
