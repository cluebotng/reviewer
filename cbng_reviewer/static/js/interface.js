let isProcessingClassification = false;

function showSpinner() {
    document.getElementById("spinner").style.display = "block";
}

function hideSpinner() {
    document.getElementById("spinner").style.display = "none";
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
            alert('Failed to classify edit');
            isProcessingClassification = false;
            hideSpinner();
            return null;
        }
        return response.json();
    })
    .then(function(data) {
        if (!data) return;

        // API wants to confirm - ask the user
        if (data["require_confirmation"]) {
            isProcessingClassification = false;
            if (!confirm("Are you sure?")) {
                hideSpinner();
                return;
            }
            classifyEdit(csrftoken, classification, true);
            return;
        }

        // We are done - onto the next
        isProcessingClassification = false;
        loadNextEditId();
    })
    .catch(function() {
        alert('Failed to classify edit');
        isProcessingClassification = false;
        hideSpinner();
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
            alert('Failed to retrieve pending edit');
            return null;
        }
        return response.json();
    })
    .then(function(data) {
        if (!data) return;
        if (data["message"]) {
            alert(data["message"]);
        } else {
            renderEdit(data["edit_id"]);
        }
    })
    .catch(function() {
        alert('Failed to retrieve pending edit');
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
