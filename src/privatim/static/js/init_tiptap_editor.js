// All TipTap dependencies can be imported here.
// Make sure to include the version number, so an update won't just break the universe.
// To find out what The Version numbers are available, you can search in https://www.npmjs.com/.

// Also, core and starterkit _need_ to be version 2.4.0.
// If you change the version, you'll probably have to change the patched dependency (Search for "XXX Patch TipTap".)
import {Editor} from 'https://esm.sh/@tiptap/core@2.4.0';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2.4.0';


import BubbleMenu from 'https://esm.sh/@tiptap/extension-bubble-menu@2.5.4';


document.addEventListener('DOMContentLoaded', function () {
    const editors = [];

    document.querySelectorAll('.tiptap-wrapper').forEach((wrapper) => {
        const element = wrapper.querySelector('.tiptap-editor');
        const inputId = element.id.replace('-editor', '');
        const inputElement = document.getElementById(inputId);
        const bubbleMenu = wrapper.querySelector('.bubble-menu');

        if (!bubbleMenu) {
            console.error('Bubble menu not found for editor:', inputId);
            return;
        }

        const editor = new Editor({
            element: element,
            extensions: [
                StarterKit,
                BubbleMenu.configure({
                    element: bubbleMenu,
                    shouldShow: ({editor, view, state, oldState, from, to}) => {
                        console.log('Checking if bubble menu should show:', from, to);
                        return from !== to; // Show menu when text is selected
                    },
                }),
            ],
            content: inputElement.value,
            onUpdate: ({editor}) => {
                inputElement.value = editor.getHTML();
            },
            onSelectionUpdate: ({editor}) => {
                console.log('Selection updated');
            },
        });

        editors.push(editor);

        // Add event listeners to bubble menu buttons
        bubbleMenu.querySelectorAll('button').forEach(button => {
            button.addEventListener('click', () => {
                const type = button.getAttribute('data-type');
                console.log('Button clicked:', type);

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
});
