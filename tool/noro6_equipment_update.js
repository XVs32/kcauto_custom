function findComponentByName(vm, name) {
    if (!vm) return null;
    if (vm.$options && vm.$options.name === name) return vm;
    for (const child of vm.$children || []) {
        const found = findComponentByName(child, name);
        if (found) return found;
    }
    return null;
}

async function runTurboAutomation() {
    const root = document.getElementById('app')?.__vue__;
    const airCalc = findComponentByName(root, 'AirCalculator');
    if (!airCalc) {
        console.error('❌ AirCalculator instance not found. Are you currently on the #/aircalc page?');
        return;
    }

    const store = airCalc.$store;
    const tabs = store.state.saveData
        .fetchActiveData()
        .sort((a, b) => a.activeOrder - b.activeOrder);

    console.log(`🚀 Starting processing for ${tabs.length} tabs...`);

    for (const [i, tab] of tabs.entries()) {
        // Equivalent to clicking this tab
        store.state.saveData.disabledMain();
        tab.isMain = true;
        store.dispatch('setMainSaveData', tab);
        await airCalc.$nextTick();

        // Equivalent to the disabled state check for the "Execute" button in the UI
        if (airCalc.disabledSync) {
            console.warn(`   ⚠️ [${i + 1}/${tabs.length}] ${tab.name}: No inventory data, skipped`);
            continue;
        }

        // Call the underlying method of the "Execute" button directly
        airCalc.syncCurrentData();
        await airCalc.$nextTick();

        console.log(`   ✅ [${i + 1}/${tabs.length}] ${tab.name} sync complete`);
    }

    console.log('✨ All processing complete!');
}

runTurboAutomation();