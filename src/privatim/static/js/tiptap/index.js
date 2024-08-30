import { Editor } from '@tiptap/core';
import { StarterKit } from '@tiptap/starter-kit';
import { BubbleMenu } from '@tiptap/extension-bubble-menu';
import { Link } from '@tiptap/extension-link';

// Export the symbols we need as globals
window.tiptap = {
    Editor: Editor,
    StarterKit: StarterKit,
    BubbleMenu: BubbleMenu,
    Link: Link
};
