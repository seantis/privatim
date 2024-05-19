$(function() {
    var table = null;
    var active_row = null;
    var active_popover = null;
    var popover_timeout = null;
    function _unescape(string) {
        return string
            .replace(/&gt;/g, '>')
            .replace(/&lt;/g, '<')
            .replace(/&(#39|apos);/g, "'")
            .replace(/&(#34|quot);/g, '"')
            .replace(/&amp;/g, '&')
    }
    function clear_popover() {
        if (popover_timeout !== null) {
            clearTimeout(popover_timeout);
            popover_timeout = null;
        }
        if (active_popover !== null) {
            active_popover.dispose();
            active_popover = null;
        }
    }
    function popover(element, placement, message, type) {
        // dispose the old popover before showing a new one
        clear_popover();
        active_popover = new bootstrap.Popover(element, {
            content: message,
            placement: placement,
            container: 'body',
            template: '<div class="popover border-'+type+'" role="tooltip"><div class="popover-body text-'+type+'"></div></div>',
            trigger: 'custom',
        });

        active_popover.show();
        $(active_popover.tip).click(clear_popover);
        popover_timeout = setTimeout(clear_popover, 3000);
    }
    var fields = $('#edit-xhr-form').data('fields') || [];

    $('#edit-xhr').on('show.bs.modal', function(event) {
        var source = $(event.relatedTarget);
        var edit_url = source.attr('href');

        // remove old validation errors
        $('#edit-xhr-form input')
        .removeClass('is-invalid').remove('.invalid-feedback');

        var table_id = source.data('table-id');
        if (table_id) {
            // add row button
            table = $('#' + table_id).DataTable({'retrieve': true});
            active_row = 'add';
            // clear form fields
            $.each(fields, function(index, name) {
                $('#edit-xhr-'+ name).val('');
            });
        } else {
            // edit row button
            table = source.closest('table').DataTable({'retrieve': true});
            active_row = table.row(source.closest('tr'));
            var row_data = active_row.data();
            $.each(fields, function(index, name) {
                var value = row_data[name];

                if (!value) {
                    console.log('Undefined value for field:', name, 'Generally it is assumed that _all_ fields on the form are part of the table');
                }

                $('#edit-xhr-'+ name).val(value ? _unescape(value) : '');
            });
        }

        $('#edit-xhr-form').attr('action', edit_url);
    });

    // focus first form field
    if (fields.length > 0) {
        $('#edit-xhr').on('shown.bs.modal', function(event) {
            $('#edit-xhr-'+ fields[0]).trigger('focus');
        });
    }

    $('#delete-xhr').on('show.bs.modal', function(event) {
        var source = $(event.relatedTarget);
        var title = source.data('item-title');
        var delete_url = source.attr('href');

        table = source.closest('table').DataTable({'retrieve': true});
        active_row = table.row(source.closest('tr'));

        $('#delete-xhr-item-title').text(title);
        $('#delete-xhr .btn-danger').attr('href', delete_url);
    });

    $('#delete-xhr .btn-danger').on('click', function(event) {
        event.preventDefault();
        var btn = $(this);
        var delete_url = btn.attr('href');
        var csrf_token = btn.data('csrf-token');
        $.ajax({
            url: delete_url,
            type: 'DELETE',
            headers: {'X-CSRF-Token': csrf_token},
            dataType: 'json',
            cache: false,
        }).done(function(data) {
            var node = active_row.node();
            var neighbour, placement;
            if (node.nextElementSibling !== null) {
                neighbour = node.nextElementSibling;
                placement = 'top';
            } else if (node.previousElementSibling !== null) {
                neighbour = node.previousElementSibling;
                placement = 'bottom';
            } else {
                neighbour = node.parent;
                placement = 'bottom';
            }
            var neighbour = node.nextElementSibling || node.previousElementSibling;
            popover(neighbour, placement, data['success'], 'success');
            active_row.remove().clearPipeline().draw(false);
        });
        var modal = document.getElementById('delete-xhr');
        bootstrap.Modal.getInstance(modal).hide();
        return false;
    });

    function enable_submits(buttons) {
        if(!buttons.attr('aria-disabled')) {
            return
        }
        buttons.removeClass('disabled');
        buttons.removeAttribute('aria-disabled');
        buttons.each(function(index, element) {
            var btn = new bootstrap.Button(element);
            btn.toggle();
        });
    }

    $('#edit-xhr-form').on('submit', function(event) {
        event.preventDefault();
        var form = $(this);
        var edit_url = form.attr('action');
        var button = form.find('.submit-button');
        $.post(edit_url, form.serialize(), function(data) {
            form.find('input').removeClass('is-invalid');
            form.find('.invalid-feedback').remove();
            if(data['errors']) {
                $.each(data['errors'], function(key, value) {
                    var feedback = $('<div class="invalid-feedback"></div>').text(value);
                    var field = $('#edit-xhr-'+key);
                    field.addClass('is-invalid').parent().append(feedback);
                });
                enable_submits(button);
            } else {
                if (active_row === 'add') {
                    // add a new row
                    var row_data = {};
                    $.each(fields, function(index, name) {
                        row_data[name] = data[name];
                    });
                    row_data['buttons'] = data['buttons'];
                    row_data['DT_RowId'] = data['DT_RowId'];

                    // drawing could be deferred so we need an event handler
                    // to respond to the newly added row being drawn once
                    table.one('draw', function() {
                        var node = document.getElementById(data['DT_RowId']);
                        // have a sane fallback if the row doesn't exist, because
                        // it e.g. scrolled past the end of the page
                        if(node === null) {
                            var nodes = table.rows({page: 'current'}).nodes();
                            if(nodes.length === 0) {
                                node = table.table().body();
                            } else {
                                node = nodes[Math.ceil(nodes.length/2)];
                            }
                        }
                        popover(node, 'top', data['message'], 'success');
                    });
                    table.row.add_xhr(row_data).draw(false);
                } else {
                    // edit existing row
                    var row_data = active_row.data();
                    $.each(fields, function(index, name) {
                        row_data[name] = data[name];
                    });
                    active_row.data(row_data);
                }
                var modal = document.getElementById('edit-xhr');
                bootstrap.Modal.getInstance(modal).hide();

                // reset the active row and table
                table = null;
                active_row = null;
            }
        });
        return false;
    });
});
