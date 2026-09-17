// ==UserScript==
// @name         KC-Web AirCalc Turbo Sync
// @namespace    https://xvs32.github.io/kc-web/
// @version      1.0.0
// @description  Batch sync fleet/air base data of every saved tab to the current ship/equipment inventory via Vue/Vuex internal methods.
// @author       XVs32
// @match        https://xvs32.github.io/kc-web/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    const PANEL_ID = 'turbo-sync-panel';

    /* ---------- Core Logic ---------- */

    function findComponentByName(vm, name) {
        if (!vm) return null;
        if (vm.$options && vm.$options.name === name) return vm;
        for (const child of vm.$children || []) {
            const found = findComponentByName(child, name);
            if (found) return found;
        }
        return null;
    }

    function getAirCalcInstance() {
        const root = document.getElementById('app')?.__vue__;
        if (!root) return null;
        return findComponentByName(root, 'AirCalculator');
    }

    async function runTurboAutomation(log) {
        const airCalc = getAirCalcInstance();
        if (!airCalc) {
            log('❌ AirCalculator instance not found. Please make sure you are on the #/aircalc page and data is fully loaded.', true);
            return;
        }

        const store = airCalc.$store;
        const saveDataRoot = store.state.saveData;
        if (!saveDataRoot) {
            log('❌ saveData not found. Please make sure there is at least one saved tab on the left.', true);
            return;
        }

        const tabs = saveDataRoot.fetchActiveData().sort((a, b) => a.activeOrder - b.activeOrder);

        if (!tabs.length) {
            log('⚠️ No active tabs available to process.', true);
            return;
        }

        log(`🚀 Starting processing for ${tabs.length} tabs...`);

        for (const [i, tab] of tabs.entries()) {
            // Equivalent to clicking this tab
            saveDataRoot.disabledMain();
            tab.isMain = true;
            store.dispatch('setMainSaveData', tab);
            await airCalc.$nextTick();

            // Equivalent to the disabled state check for the "Execute" button in the UI
            if (airCalc.disabledSync) {
                log(`⚠️ [${i + 1}/${tabs.length}] ${tab.name}: No inventory data, skipped`);
                continue;
            }

            // Call the method behind the "Execute" button directly
            airCalc.syncCurrentData();
            await airCalc.$nextTick();
            log(`✅ [${i + 1}/${tabs.length}] ${tab.name} sync complete`);
        }

        log('✨ All processing complete!');
    }

    /* ---------- Floating Panel UI ---------- */
    // Do not execute automatically right after page load, as SPA data (ship/equipment inventory,
    // saved tabs) takes time to load asynchronously. Provide a button to trigger manually.

    function injectPanel() {
        if (document.getElementById(PANEL_ID)) return;

        const panel = document.createElement('div');
        panel.id = PANEL_ID;
        Object.assign(panel.style, {
            position: 'fixed',
            right: '12px',
            bottom: '12px',
            zIndex: 999999,
            background: 'rgba(30,30,30,0.95)',
            color: '#eee',
            fontSize: '12px',
            fontFamily: 'sans-serif',
            borderRadius: '8px',
            padding: '8px',
            width: '280px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
        });

        const button = document.createElement('button');
        button.textContent = '⚡ Turbo Sync All Tabs';
        Object.assign(button.style, {
            width: '100%',
            padding: '6px',
            cursor: 'pointer',
            border: 'none',
            borderRadius: '4px',
            background: '#4caf50',
            color: '#fff',
            fontWeight: 'bold',
        });

        const logBox = document.createElement('div');
        Object.assign(logBox.style, {
            marginTop: '6px',
            maxHeight: '160px',
            overflowY: 'auto',
            whiteSpace: 'pre-wrap',
            lineHeight: '1.4',
        });

        const log = (msg, isError) => {
            const line = document.createElement('div');
            line.textContent = msg;
            if (isError) line.style.color = '#ff6b6b';
            logBox.appendChild(line);
            logBox.scrollTop = logBox.scrollHeight;
            console.log(msg);
        };

        button.addEventListener('click', async () => {
            button.disabled = true;
            logBox.innerHTML = '';
            try {
                await runTurboAutomation(log);
            } catch (e) {
                log(`❌ Exception occurred: ${e.message}`, true);
                console.error(e);
            } finally {
                button.disabled = false;
            }
        });

        panel.appendChild(button);
        panel.appendChild(logBox);
        document.body.appendChild(panel);
    }

    // Inject panel once #app is mounted (SPA initial load might be slightly slower than document-idle)
    const waitForApp = setInterval(() => {
        if (document.getElementById('app')?.__vue__) {
            clearInterval(waitForApp);
            injectPanel();
        }
    }, 300);
})();