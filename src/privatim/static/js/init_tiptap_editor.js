// If you change the version, you'll probably have to change the import map as well. Search for "XXX Patch TipTap".

import { Editor } from 'https://esm.sh/@tiptap/core@2.4.0'
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2.4.0'

document.addEventListener('DOMContentLoaded', function () {

    document.querySelectorAll('.element').forEach((element) => {
        const inputId = element.id.replace('-editor', '');
        const inputElement = document.getElementById(inputId);

        const editor = new Editor({
            element: element,
            extensions: [StarterKit],
            content: inputElement.value,
            onUpdate: ({editor}) => {
                inputElement.value = editor.getHTML();
            }
        });
    });

});
