import Sortable from '../sortable.core.esm.js';



/*
    This module scans the page for elements which have the
    'data-sortable' attribute set. Those that do are expected to also have a
    'data-sortable-url' attribute which should look like this:

    https://example.xxx/yyy/{subject_id}/{direction}/{target_id}

    This enables drag&drop sorting on the list. Each time an element is
    moved around, the url is called with the following variables replaced:

    * subject_id: the id of the item moved around
    * target_id: the id above which or below which the subject is moved
    * direction: the direction relative to the target ('above' or 'below')

    For example, this url would move id 1 below id 3:
    .../1/below/3

    The ids are taken from the item's 'data-sortable-id' attribute.
*/

var on_move_element = function(container, element, new_index, old_index) {
    var siblings = $(container).children();

    if (siblings.length < 2) {
        return;
    }

    var target = new_index === 0 ? siblings[1] : siblings[new_index - 1];
    var direction = new_index === 0 ? 'above' : 'below';
    var url = decodeURIComponent($(container).data('sortable-url'))
        .replace('{subject_id}', $(element).data('sortable-id'))
        .replace('{target_id}', $(target).data('sortable-id'))
        .replace('{direction}', direction);

    const containsUndefiendStr = (url) => { return url.includes('undefined') }
    console.assert(!containsUndefiendStr(url))

    const csrf_token = document.querySelector('input[name="csrf_token"]').value;
    $.ajax({
        type: "POST", url: url, headers: {
            'X-CSRF-Token': csrf_token
        },
        dataType: 'json',
        cache: false,
    })
        .done(function () {
            $(element).addClass('flash').addClass('success');
            updateIndexes(container);
        })
        .fail(function () {
            undo_move_element(container, element, new_index, old_index);
            $(element).addClass('flash').addClass('failure');
        })
        .always(function () {
            setTimeout(function () {
                $(element)
                    .removeClass('flash')
                    .removeClass('success')
                    .removeClass('failure');
            }, 1000);
        });
};

function updateIndexes(container) {
    // We could use a sophisticated way to update the indexes in-place, but I mean, why?
    // Keep it simple
    window.location.reload();
}

var undo_move_element = function(container, element, new_index, old_index) {
    var siblings = $(container).children();

    if (old_index === 0) {
        $(element).insertBefore($(siblings[0]));
    } else {
        if (old_index <= new_index) {
            // was moved down
            $(element).insertAfter($(siblings[old_index - 1]));
        } else {
            // was moved up
            $(element).insertAfter($(siblings[old_index]));
        }
    }
};

var setup_sortable_container = function(container_element) {
    var container = $(container_element);
    var start = null;

    var sortable = Sortable.create(container_element, {
        animation: 150,
        group: 'list-1',
        handle: '.handle-for-dragging',  // the element which is actually the "hitbox" for dragging
        sort: true,
        chosenClass: 'active',
        onStart: function(event) {
            if ($(event.element).parent().hasClass('children')) {
                return;
            }

            // add an element at the bottom if the last item has children,
            // otherwise it's not possible to drop elements below it, as
            // there's no actual drop-area
            var last_element = container.children().last();

            if (last_element.find('.children').length !== 0) {
                container.append($('<div class="empty">&nbsp;</div>'));
            }

            start = (new Date()).getTime();
        },
        onEnd: function(event) {
            container.find('> .empty').remove();

            var new_index = event.newIndex;

            if (new_index >= container.children().length) {
                new_index = container.children().length - 1;
            }

            // only continue with the drag & drop operation if the whole thing
            // took more than 200ms, below that we assume it was an accident
            if (new_index != event.oldIndex) {
                if (((new Date()).getTime() - start) <= 200) {
                    undo_move_element(container_element, event.item, new_index, event.oldIndex);
                } else {
                    on_move_element(container_element, event.item, new_index, event.oldIndex);
                }
            }
        }
    });

    container.children().each(function() {
        this.addEventListener('dragstart', function(event) {
            $(event.target).addClass('dragging');
        });
    });
};


(function($) {
    $(document).ready(function() {
        $('[data-sortable]').each(function() {
            setup_sortable_container(this);
        });
    });
})(jQuery);
