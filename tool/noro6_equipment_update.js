/**
 * Helper: Checks if an element is actually visible to the user
 */
const isVisible = (el) => {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        style.opacity !== '0' &&
        el.offsetParent !== null;
};

/**
 * Helper: Wait for element to be visible
 */
const waitForVisible = (selector, timeout = 4000) => {
    return new Promise((resolve) => {
        const startTime = Date.now();
        const timer = setInterval(() => {
            const el = document.querySelector(selector);
            if (isVisible(el) || (Date.now() - startTime) > timeout) {
                clearInterval(timer);
                resolve(el);
            }
        }, 50);
    });
};

/**
 * Helper: Wait for element (or modal) to be HIDDEN or REMOVED
 */
const waitForHidden = (selector, timeout = 4000) => {
    return new Promise((resolve) => {
        const startTime = Date.now();
        const timer = setInterval(() => {
            const el = document.querySelector(selector);
            // Resolved if element is gone OR is no longer visible
            if (!el || !isVisible(el) || (Date.now() - startTime) > timeout) {
                clearInterval(timer);
                resolve();
            }
        }, 50);
    });
};

async function runTurboAutomation() {
    const container = document.querySelector('#active-tab-list .d-flex');
    const tabItems = Array.from(container.querySelectorAll('.tab-item'));

    console.log(`🚀 Starting Smart-Turbo Mode for ${tabItems.length} tabs...`);

    for (let i = 0; i < tabItems.length; i++) {
        console.log(`[${i + 1}/${tabItems.length}] Processing Tab...`);

        tabItems[i].click();

        // 1. Wait for Sync Button
        const syncIcon = await waitForVisible('.mdi-database-sync');
        const syncButton = syncIcon?.closest('button');

        if (syncButton) {
            syncButton.click();

            // 2. Wait for Execute (Success) Button
            const executeBtn = await waitForVisible('button.success');
            if (executeBtn) {
                executeBtn.click();
                console.log("   ✅ Executed. Waiting for UI to clear...");

                // Wait for the specific button OR the general dialog to hide
                // We check for both the button and the common Vuetify overlay class
                await Promise.race([
                    waitForHidden('button.success'),
                    waitForHidden('.v-dialog--active'),
                    new Promise(r => setTimeout(r, 1000)) // Safety fallback: max 1s wait
                ]);
            }
        } else {
            console.warn(`   ⚠️ Sync icon not found for tab ${i + 1}`);
        }
    }

    console.log("✨ All tasks finished successfully!");
}

runTurboAutomation();