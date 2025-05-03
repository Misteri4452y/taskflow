// Waits for the DOM to fully load before running the script
document.addEventListener("DOMContentLoaded", function () {
    const manualToggle = document.getElementById('manual-time-toggle'); // Checkbox to toggle manual scheduling
    const manualFields = document.getElementById('manual-time-fields'); // Div for manual input fields (day & time)
    const autoFields = document.getElementById('auto-fields'); // Div for automatic scheduling fields (deadline)

    // Ensure all required elements exist before attaching logic
    if (manualToggle && manualFields && autoFields) {
        manualToggle.addEventListener('change', function () {
            const showManual = this.checked;
            manualFields.style.display = showManual ? 'block' : 'none';
            autoFields.style.display = showManual ? 'none' : 'block';
        });
    }
});
