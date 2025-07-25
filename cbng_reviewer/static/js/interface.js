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
    let editId = document.getElementById("edit_id").innerText;
    console.debug("Classifying " + editId + " as " + classification + " (" + confirmation + ")");
    showSpinner();

    let req = new XMLHttpRequest();
    req.onreadystatechange = function(){
        if (this.readyState !== 4) {
            return;
        }

        if (this.status !== 200) {
            alert('Failed to classify edit');
            return;
        }

        // API wants to confirm - ask the user
        let require_confirmation = JSON.parse(this.responseText)["require_confirmation"];
        if (require_confirmation) {
            let confirmation = confirm("Are you sure?");
            if (!confirmation) {
                hideSpinner();
                return;
            }
            return classifyEdit(csrftoken, classification, true);
        }

        // We are done - onto the next
        loadNextEditId();
    }
    req.open("POST", "/api/v1/reviewer/classify-edit/", true);
    req.setRequestHeader("Content-Type", "application/json;charset=UTF-8");
    req.setRequestHeader("X-CSRFToken", csrftoken);
    req.send(JSON.stringify({
        "edit_id": parseInt(editId),
        "comment": document.getElementById("comment").value,
        "classification": classification,
        "confirmation": confirmation,
    }));
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
        document.getElementById("iframe").setAttribute("src", url);
        iframe.onload = function() { hideSpinner(); }
    }
}

function loadNextEditId() {
    document.getElementById("comment").value = "";

    let req = new XMLHttpRequest();
    req.onreadystatechange = function(){
        if (this.readyState !== 4) {
            return;
        }

        if (this.status !== 200) {
            alert('Failed to retrieve pending edit');
            return;
        }

        let data = JSON.parse(this.responseText);
        if (data["message"]) {
            alert(data["message"]);
        } else {
            renderEdit(data["edit_id"]);
        }
    }
    req.open("GET", "/api/v1/reviewer/next-edit/", true);
    req.send();
}

function loadDetails() {
    let editId = document.getElementById("edit_id").innerText;
    window.open("/admin/edit/" + editId + "/", true);
}

window.onload = function() {
    showSpinner();
    loadNextEditId();
}
