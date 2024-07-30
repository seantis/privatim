// All TipTap dependencies can be imported here.
// Make sure to include the version number, so an update won't just break the universe.
// To find out what The Version numbers are available, you can search in https://www.npmjs.com/.

// Also, core and starterkit _need_ to be version 2.4.0.
// If you change the version, you'll probably have to change the patched dependency (Search for "XXX Patch TipTap".)
import {Editor} from 'https://esm.sh/@tiptap/core@2.4.0';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2.4.0';


import BubbleMenu from 'https://esm.sh/@tiptap/extension-bubble-menu@2.5.4';
import Link from 'https://esm.sh/@tiptap/extension-link@2.4.0';
import Paragraph from 'https://esm.sh/@tiptap/extension-paragraph@2.4.0';
import Document from 'https://esm.sh/@tiptap/extension-document';
import Text from 'https://esm.sh/@tiptap/extension-text@2.4.0';
import Code from 'https://esm.sh/@tiptap/extension-code@2.4.0';


const editors = [];

document.querySelectorAll('.tiptap-wrapper').forEach((wrapper) => {
    const element = wrapper.querySelector('.element');
    const inputId = element.id.replace('-editor', '');
    const inputElement = document.getElementById(inputId);
    const bubbleMenu = wrapper.querySelector('.bubble-menu');

    [...document.getElementsByClassName('element')].forEach((el) => {
        el.addEventListener('click', function (event) {
            // Make sure the click on the whole field is forwarded to act like a click on the editor.
            // event.preventDefault();
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
            Document,
            Paragraph,
            Text,
            Code,
            Link.configure({
                openOnClick: true,
                autolink: true,  // Add links as you type
            }),
            BubbleMenu.configure({
                element: bubbleMenu,
                shouldShow: ({editor, view, state, oldState, from, to}) => {
                    return from !== to; // Show menu when text is selected
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
                // Add more cases for other button types
                default:
                    console.warn('Unhandled button type:', type);
            }
        });
    });
});

// You can now access all editors if needed
console.log('Total editors initialized:', editors.length);
