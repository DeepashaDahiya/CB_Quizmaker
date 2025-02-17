function navigateTo(page) {
    window.location.href = page;
}

function toggleMenu() {
    document.querySelector("nav").classList.toggle("show");
}

// let lastScrollTop = 0;
// const header = document.querySelector("header");

// window.addEventListener("scroll", function () {
//     let scrollTop = window.scrollY || document.documentElement.scrollTop;

//     if (scrollTop > lastScrollTop) {
//         // Scrolling down → Hide header
//         header.style.top = `-${header.offsetHeight}px`;
//     } else {
//         // Scrolling up → Show header
//         header.style.top = "0";
//     }

//     lastScrollTop = scrollTop;
// });

window.onload = function () {
    const summarizeButton = document.getElementById("summarizeButton");

    if (!summarizeButton) {
        console.error("Summarize button not found!");
        return;
    }

    console.log("Summarize button detected, adding event listener...");

    summarizeButton.addEventListener("click", function () {
        console.log("Summarize button clicked!");

        let summaryType = document.querySelector('input[name="summaryType"]:checked').value;
        let topic = document.getElementById("topicInput").value.trim();
        let summaryOutput = document.getElementById("summaryText");

        if (summaryType === "specific" && topic === "") {
            alert("Please enter a topic to summarize!");
            return;
        }

        let url = summaryType === "entire" ? "/summarize_entire" : "/summarize_specific";
        let bodyData = summaryType === "entire" ? {} : { topic: topic };

        // ✅ Show "Fetching summary..." before sending request
        summaryOutput.innerText = "⏳ Fetching summary... Please wait.";
        summaryOutput.style.color = "blue";

        fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bodyData),
        })
        .then(response => response.json())
        .then(data => {
            console.log("Response received:", data);
            summaryOutput.innerText = data.summary;  // ✅ Replace with actual summary
            summaryOutput.style.color = "black";  // ✅ Reset text color
        })
        .catch(error => {
            console.error("Fetch error:", error);
            summaryOutput.innerText = "❌ Error fetching summary. Please try again.";
            summaryOutput.style.color = "red";  // ✅ Show error in red
        });
    });
};
// document.addEventListener("DOMContentLoaded", function () {
//     console.log("JavaScript Loaded");

//     let analyzeButton = document.getElementById("analyzeButton");
//     let uploadButton = document.getElementById("uploadButton");

//     if (analyzeButton) {
//         analyzeButton.addEventListener("click", function () {
//             console.log("Analyze Gaps button clicked! Sending request...");
//             analyzeGaps();
//         });
//     } else {
//         console.error("Analyze Gaps button not found!");
//     }

//     if (uploadButton) {
//         uploadButton.addEventListener("click", function () {
//             console.log("Upload button clicked! Sending request...");
//             uploadSyllabus();
//         });
//     } else {
//         console.error("Upload button not found!");
//     }
// });
document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("analyzeButton").addEventListener("click", function () {
        analyzeGaps();
    });
});


// function analyzeGaps() {
//     console.log("Sending request to /analyze_gaps");

//     fetch("/analyze_gaps", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" }
//     })
//     .then(response => response.json())
//     .then(data => {
//         console.log("Response received:", data);
//         document.getElementById("gapOutput").innerText = data.missing_topics ? data.missing_topics.join(", ") : "No missing topics found.";
//     })
//     .catch(error => {
//         console.error("Error:", error);
//         document.getElementById("gapOutput").innerText = "Error analyzing gaps.";
//     });
// }
function analyzeGaps() {
    console.log("Analyze Gaps button clicked! Sending request...");

    fetch("/analyze_gaps", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            console.error("Backend Error:", data.error);
            document.getElementById("gapOutput").innerText = "Error: " + data.error;
        } else {
            document.getElementById("gapOutput").innerText = data.missing_topics.join(", ");
        }
    })
    .catch(error => {
        console.error("Fetch Error:", error);
        document.getElementById("gapOutput").innerText = "Error analyzing gaps.";
    });
}


function uploadSyllabus() {
    let syllabusFile = document.getElementById("syllabusUpload").files[0];
    if (!syllabusFile) {
        alert("Please select a syllabus file to upload.");
        return;
    }

    let formData = new FormData();
    formData.append("syllabusUpload", syllabusFile);

    console.log("Uploading syllabus file:", syllabusFile.name);

    fetch("/upload_syllabus", {
        method: "POST",
        body: formData
    })
    .then(response => {
        if (response.ok) {
            console.log("Syllabus uploaded successfully");
        } else {
            console.log("Failed to upload syllabus");
            alert("Failed to upload syllabus.");
        }
    })
    .catch(error => {
        console.error("Upload error:", error);
        alert("Error uploading syllabus.");
    });
}


