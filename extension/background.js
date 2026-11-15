'use strict';
chrome.action.onClicked.addListener(tab => {
  chrome.storage.session.set({targetTab: tab.id});
  chrome.sidePanel.open({windowId: tab.windowId});
});
