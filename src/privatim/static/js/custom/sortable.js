
import Sortable from '../sortable.core.esm.js';


document.addEventListener('DOMContentLoaded', () => {
    Sortable.create(document.getElementById('agenda-items'), {
        animation: 150,
        group: 'list-1',
        // draggable: '.draggable-item',
        handle: '.handle',
        sort: true,
        filter: '.sortable-disabled',
        chosenClass: 'active'
    });
});
