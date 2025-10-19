// ==================== Tab Control ====================
// This file handles the tab switching functionality in the settings page

/**
 * Open a specific tab and hide others
 * @param {Event} evt - The click event
 * @param {string} tabName - The ID of the tab to open
 */
window.openTab = function(evt, tabName) {
    let i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].classList.remove('active', 'visible');
    }
    tablinks = document.getElementsByClassName("tab-link");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].classList.remove('active');
    }
    
    const activeTab = document.getElementById(tabName);
    activeTab.classList.add('active');
    evt.currentTarget.classList.add('active');

    setTimeout(() => {
        activeTab.classList.add('visible');
    }, 10);
}