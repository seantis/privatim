// All TipTap dependencies can be imported here.
// Make sure to include the version number, so an update won't just break the universe.
// To find out what The Version numbers are available, you can search in https://www.npmjs.com/.
// Also, core and starterkit *need* to be version 2.4.0.
// If you change the version, you'll probably have to change the patched dependency (Search for "XXX Patch TipTap".)
import {Editor} from 'https://esm.sh/@tiptap/core@2.4.0';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2.4.0';
import BubbleMenu from 'https://esm.sh/@tiptap/extension-bubble-menu@2.5.4';
import Link from 'https://esm.sh/@tiptap/extension-link@2.4.0';

const editors = [];

document.querySelectorAll('.tiptap-wrapper').forEach((wrapper) => {
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
            // Document,
            // Paragraph,
            // Text,
            // Code,
            Link.configure({
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
