// All TipTap dependencies can be imported here.
// Make sure to include the version number, so an update won't just break the universe.
// To find out what The Version numbers are available, you can search in https://www.npmjs.com/.

// Also, core and starterkit _need_ to be version 2.4.0.
// If you change the version, you'll probably have to change the patched dependency (Search for "XXX Patch TipTap".)
import {Editor} from 'https://esm.sh/@tiptap/core@2.4.0';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2.4.0';


import BubbleMenu from 'https://esm.sh/@tiptap/extension-bubble-menu@2.5.4';


document.addEventListener('DOMContentLoaded', function () {
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
                    tippyOptions: {
                        duration: 100,
                        placement: 'top',
                    },
                }),
            ],
            content: inputElement.value,
            onUpdate: ({editor}) => {
                inputElement.value = editor.getHTML();
            },
        });

        // Ensure the bubble menu is visible
        bubbleMenu.style.display = 'flex';
    });
});

