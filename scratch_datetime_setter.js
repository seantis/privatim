// Scratch file for testing datetime setting in the browser console.
// IIFE (Immediately Invoked Function Expression) to avoid polluting global scope.

(function() {
    // --- Configuration ---
    // Set the CSS selector for your datetime-local input field here
    const selector = 'input[name="time"]'; // Example selector, change as needed

    // Set the desired date and time string in 'YYYY-MM-DDTHH:MM' format
    // Example: Set to 2025-04-15 at 14:30
    const dateTimeString = '2025-04-15T14:30';
    // --- End Configuration ---


    console.log(`Attempting to set datetime for selector: "${selector}" with value: "${dateTimeString}"`);

    const element = document.querySelector(selector);

    if (!element) {
        console.error(`Datetime field with selector "${selector}" not found.`);
        return; // Exit if element not found
    }

    if (element.type !== 'datetime-local') {
         console.warn(`Element found with selector "${selector}", but it's not type="datetime-local". It's type="${element.type}". The script might not work as expected.`);
    }

    try {
        // Ensure element is visible/interactable (basic check)
        if (element.offsetParent === null) {
             console.warn(`Element with selector "${selector}" might not be visible. Attempting to scroll into view.`);
             // Attempt to scroll into view if possible from JS
             element.scrollIntoViewIfNeeded ? element.scrollIntoViewIfNeeded() : element.scrollIntoView();
        }

        // Set the value directly
        console.log('Setting element.value...');
        element.value = dateTimeString;
        console.log(`Current value after setting: "${element.value}"`);


        // Dispatch events immediately after setting value
        console.log('Dispatching input event...');
        element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));

        console.log('Dispatching change event...');
        element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));

        // Optionally trigger blur as well if needed
        // console.log('Dispatching blur event...');
        // element.dispatchEvent(new Event('blur', { bubbles: true, cancelable: true }));

        console.log('Successfully set value and dispatched events.');

    } catch (error) {
        console.error(`Error setting datetime for selector "${selector}":`, error);
    }

})(); // End of IIFE
