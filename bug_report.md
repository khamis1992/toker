# Toker Web App: Blinking Issue Investigation Report

## 1. Overview

This report details the investigation into the page blinking issue observed when clicking the "Add Proxy" button in the Toker web application. The root cause has been identified as a combination of a CSS styling conflict and a secondary issue related to page reloading after form submission.

## 2. Root Cause Analysis

The blinking behavior is primarily caused by a CSS conflict between a hover effect on the parent container and the Bootstrap modal component. Here is a breakdown of the issues found:

### 2.1. Primary Cause: CSS Stacking Context Interference

The main reason for the blinking or flickering of the "Add Proxy" modal is a CSS issue. The modal's HTML is nested inside a `div` with the class `dashboard-card`. This `dashboard-card` has a CSS `:hover` effect that applies a `transform: translateY(-5px)`. 

In CSS, applying a `transform` to an element creates a new stacking context. This new stacking context interferes with the Bootstrap modal's ability to correctly position itself and its backdrop, causing it to appear and disappear rapidly, creating the blinking effect.

### 2.2. Secondary Cause: Unnecessary Page Reload

Even if the modal were to open correctly, a secondary issue would cause the page to blink after a proxy is successfully added. The JavaScript code responsible for handling the form submission (`submitAjaxForm` function in `proxies.html`) is configured to perform a full page reload (`location.reload()`) after a successful submission. This is unnecessary and contributes to a poor user experience.

### 2.3. Missing Dependency

During the investigation, a missing Python dependency, `aiohttp`, was discovered. This was causing an error on the backend when attempting to validate a new proxy, although it was not the direct cause of the blinking issue.

## 3. Recommended Solutions

To resolve the blinking issue and improve the user experience, the following changes are recommended:

### 3.1. Fix the Modal Stacking Context

The primary issue can be resolved by moving the HTML code for the `addProxyModal` outside of the `.dashboard-card` `div` in the `dashboard/templates/dashboard/proxies.html` file. The modal's HTML should be a direct child of the `body` tag or at least outside of any element with a `transform` property.

### 3.2. Prevent Unnecessary Page Reload

The secondary blinking issue can be fixed by modifying the `submitAjaxForm` function call in `proxies.html`. The `reloadAfter` parameter should be set to `false` for the 'add' action. This will prevent the page from reloading after a proxy is added, and the UI can be updated dynamically using JavaScript.

### 3.3. Install Missing Dependency

The missing `aiohttp` dependency should be added to the `requirements.txt` file and installed in the environment to ensure that proxy validation works as expected.

## 4. Conclusion

By implementing the recommended solutions, the blinking issue will be resolved, and the overall user experience of the proxy management page will be improved. The application will be more stable and responsive.
