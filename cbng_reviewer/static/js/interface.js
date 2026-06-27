let isProcessingClassification = false;

function showSpinner() {
    document.getElementById("spinner").style.display = "block";
}

function hideSpinner() {
    document.getElementById("spinner").style.display = "none";
}

function showAlert(message) {
    var p = document.createElement('p');
    p.innerText = message;

    var box = document.getElementById('modal-box');
    box.innerHTML = '';
    box.append(p);

    document.getElementById('modal-overlay').style.display = 'block';
    hideSpinner();
}

function showConfirm(message, callback) {
    var p = document.createElement('p');
    p.innerText = message;

    var buttons = document.createElement('div');

    function onKeyDown(e) {
        if (e.keyCode === 13 || e.key === 'Enter') {
            e.preventDefault();
            dismiss(true);
        }
    }

    function dismiss(result) {
        document.removeEventListener('keydown', onKeyDown);
        document.getElementById('modal-overlay').style.display = 'none';
        callback(result);
    }

    var ok = document.createElement('button');
    ok.innerText = 'Yes';
    ok.onclick = function() { dismiss(true); };
    buttons.appendChild(ok);

    var cancel = document.createElement('button');
    cancel.innerText = 'No';
    cancel.onclick = function() { dismiss(false); };
    buttons.appendChild(cancel);

    var box = document.getElementById('modal-box');
    box.innerHTML = '';
    box.append(p);
    box.append(buttons);

    document.getElementById('modal-overlay').style.display = 'block';
    document.addEventListener('keydown', onKeyDown);
    hideSpinner();
}

function refreshRender() {
    let editId = document.getElementById("edit_id").innerText;
    console.debug("Refreshing type for " + editId);
    showSpinner();
    renderEdit(editId);
}

function classifyEdit(csrftoken, classification, confirmation) {
    if (isProcessingClassification) return;
    isProcessingClassification = true;

    let editId = document.getElementById("edit_id").innerText;
    console.debug("Classifying " + editId + " as " + classification + " (" + confirmation + ")");
    showSpinner();

    fetch("/api/v1/reviewer/classify-edit/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json;charset=UTF-8",
            "X-CSRFToken": csrftoken,
        },
        body: JSON.stringify({
            "edit_id": parseInt(editId),
            "comment": document.getElementById("comment").value,
            "classification": classification,
            "confirmation": confirmation,
        }),
    })
    .then(function(response) {
        if (!response.ok) {
            showAlert('Failed to classify edit');
            isProcessingClassification = false;
            return null;
        }
        return response.json();
    })
    .then(function(data) {
        if (!data) {
            showAlert('Unexpected response from API');
            return;
        }

        // API wants to confirm - ask the user
        if (data["require_confirmation"]) {
            isProcessingClassification = false;
            showConfirm("Are you sure?", function(confirmed) {
                if (confirmed) {
                    classifyEdit(csrftoken, classification, true);
                }
            });
            return;
        }

        // We are done - onto the next
        isProcessingClassification = false;
        loadNextEditId();
    })
    .catch(function() {
        showAlert('Failed to classify edit');
        isProcessingClassification = false;
    });
}

function renderEdit(editId) {
    if (editId) {
        let urlType = "n";
        document.getElementsByName("url_type").forEach(function(radio) {
            if (radio.checked) {
                urlType = radio.value;
            }
        });
        console.debug("Rendering: " + editId + " using " + urlType);
        let url = "https://en.wikipedia.org/w/index.php?action=view&diff=" + editId;
        if (urlType === "d") {
            url = "https://en.wikipedia.org/w/index.php?action=view&diffonly=1&diff=" + editId;
        } else if (urlType === "r") {
            url = "https://en.wikipedia.org/w/index.php?action=render&diffonly=1&diff=" + editId;
        }
        document.getElementById("edit_id").innerText = editId;
        let iframe = document.getElementById("iframe");
        iframe.setAttribute("src", url);
        iframe.onload = function() { hideSpinner(); }
    }
}

function loadNextEditId() {
    document.getElementById("comment").value = "";

    fetch("/api/v1/reviewer/next-edit/")
    .then(function(response) {
        if (!response.ok) {
            showAlert('Failed to retrieve pending edit');
            return null;
        }
        return response.json();
    })
    .then(function(data) {
        if (!data) {
            showAlert('Unexpected response from API');
        } else if (data["message"]) {
            showAlert(data["message"]);
        } else {
            renderEdit(data["edit_id"]);
        }
    })
    .catch(function() {
        showAlert('Failed to retrieve pending edit');
    });
}

function loadDetails() {
    let editId = document.getElementById("edit_id").innerText;
    window.open("/admin/edit/" + editId + "/", "_blank");
}

window.onload = function() {
    showSpinner();
    loadNextEditId();
}

// Basic error reporting
function reportClientError(message, source, lineno, colno, stack) {
    fetch("/api/v1/internal/client-error/", {
        method: "POST",
        credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": csrftoken},
        body: JSON.stringify({
            message: String(message || ""),
            source: source || null,
            lineno: lineno || null,
            colno: colno || null,
            stack: stack || null,
            page_url: window.location.href,
        }),
    }).catch(function(e) {});
}

window.onerror = function(message, source, lineno, colno, error) {
    reportClientError(message, source, lineno, colno, error ? error.stack : null);
    return false;
};

window.addEventListener("unhandledrejection", function(event) {
    const error = event.reason;
    reportClientError(
        error instanceof Error ? error.message : String(error),
        null, null, null,
        error instanceof Error ? error.stack : null
    );
});
