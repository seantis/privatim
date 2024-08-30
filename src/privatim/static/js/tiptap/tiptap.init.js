const editors = [];


document.addEventListener('DOMContentLoaded', function () {

        console.log('Tiptap initialization starting...');
    console.log('window.tiptap:', window.tiptap);

    if (!window.tiptap) {
        console.error('Tiptap modules not found on window object');
        return;
    }

    const { Editor, StarterKit, BubbleMenu, Link } = window.tiptap;

    const CustomLink = Link.configure({
        openOnClick: true,
        linkOnPaste: true,
        autolink: true,
        HTMLAttributes: {
            target: '_blank',
            rel: 'noopener noreferrer nofollow',
            class: null
        },
    });

    document.querySelectorAll('.tiptap-wrapper').forEach((wrapper) => {
        console.log('setting up an editor');

        const element = wrapper.querySelector('.element');
        const inputId = element.id.replace('-editor', '');
        const inputElement = document.getElementById(inputId);
        const bubbleMenu = wrapper.querySelector('.bubble-menu');

        [...document.getElementsByClassName('element')].forEach((el) => {
            el.addEventListener('click', function (event) {
                let proseMirror = el.querySelector('.ProseMirror.editor-probs');
                proseMirror.focus();
            });
        });
        // The actual bubble menu structure is defined in macros.pt/render_editor
        if (!bubbleMenu) {
            return;
        }

        const editor = new Editor({
            editorProps: {
                attributes: {
                    class: 'editor-probs',
                },
            },
            element: element,
            extensions: [
                StarterKit,
                CustomLink.configure({
                    openOnClick: false,
                    linkOnPaste: true,
                    HTMLAttributes: {
                        rel: 'noopener noreferrer nofollow',
                        target: '_blank',
                    },
                }),
                BubbleMenu.configure({
                    element: bubbleMenu,
                    shouldShow: ({editor, view, state, oldState, from, to}) => {
                        return from !== to;
                    },
                    tippyOptions: {
                        onHide: () => {
                            // Clear the selection when the bubble menu hides
                            editor.commands.setTextSelection({
                                from: editor.state.selection.from,
                                to: editor.state.selection.from
                            });
                        },
                    },
                }),
            ],
            content: inputElement.value,
            onUpdate: ({editor}) => {
                inputElement.value = editor.getHTML();
            },
        });

        editors.push(editor);

        // Add event listeners to bubble menu buttons
        bubbleMenu.querySelectorAll('button').forEach(button => {
            button.addEventListener('click', () => {
                const type = button.getAttribute('data-type');
                switch (type) {
                    case 'bold':
                        editor.chain().focus().toggleBold().run();
                        break;
                    case 'italic':
                        editor.chain().focus().toggleItalic().run();
                        break;
                    case 'link':
                        setLink(editor);
                        break;
                    case 'unlink':
                        editor.chain().focus().unsetLink().run();
                        break;
                    default:
                        console.warn('Unhandled button type:', type);
                }
            });
        });
    });


    function setLink(editor) {
        const previousUrl = editor.getAttributes('link').href;
        const url = window.prompt('URL', previousUrl);

        if (url === null) {
            return;
        }

        if (url === '') {
            editor.chain().focus().extendMarkRange('link').unsetLink().run();
            return;
        }

        editor.chain().focus().extendMarkRange('link').setLink({href: url}).run();
    }

    console.log('Total editors initialized:', editors.length);
});
