const API_URL = "http://127.0.0.1:5000";

let chartInstance = null;
let categoryChartInstance = null;
let bulkImpactChartInstance = null;

function fetchEcoScore() {
    const scoreDisplay = document.getElementById("scoreDisplay");
    const pointsDisplay = document.getElementById("pointsDisplay");
    
    fetch(`${API_URL}/eco-score`)
        .then(response => {
            if (response.status === 401) {
                window.location.href = '/login.html';
                throw new Error("Unauthorized");
            }
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.json();
        })
        .then(data => {
            if (scoreDisplay) {
                scoreDisplay.textContent = data.eco_score;
                scoreDisplay.classList.add("score-loaded");
            }
            if (pointsDisplay) {
                pointsDisplay.textContent = data.eco_points;
                pointsDisplay.classList.add("score-loaded");
            }
        })
        .catch(error => {
            console.error("Error:", error);
            if (scoreDisplay) {
                scoreDisplay.textContent = "Error loading score";
                scoreDisplay.classList.add("error");
            }
        });
}

function fetchMonthlyExpenses() {
    fetch(`${API_URL}/api/monthly-expenses`)
        .then(response => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.json();
        })
        .then(data => {
            displayChart(data);
        })
        .catch(error => {
            console.error("Error fetching monthly expenses:", error);
        });
}

function displayChart(data) {
    const ctx = document.getElementById("expensesChart");
    
    if (!ctx) {
        console.error("Canvas element not found");
        return;
    }

    // Destroy existing chart if it exists
    if (chartInstance) {
        chartInstance.destroy();
    }

    chartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: "Monthly Expenses",
                    data: data.values,
                    backgroundColor: "rgba(102, 126, 234, 0.6)",
                    borderColor: "rgba(102, 126, 234, 1)",
                    borderWidth: 2,
                    borderRadius: 5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: "top"
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return "$" + value;
                        }
                    }
                }
            }
        }
    });
}













function fetchCategoryData() {
    fetch(`${API_URL}/api/spending-data`)
        .then(response => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.json();
        })
        .then(data => {
            displayCategoryChart(data);
        })
        .catch(error => {
            console.error("Error fetching category data:", error);
        });
}

const COLORS_SPENDING = [
    "rgba(102, 126, 234, 0.6)",
    "rgba(54, 162, 235, 0.6)",
    "rgba(75, 192, 192, 0.6)",
    "rgba(153, 102, 255, 0.6)",
    "rgba(201, 203, 207, 0.6)"
];

const COLORS_CARBON = ["rgba(255, 99, 132, 0.6)", "rgba(255, 159, 64, 0.6)", "rgba(255, 205, 86, 0.6)", "rgba(231, 233, 237, 0.6)", "rgba(255, 159, 64, 0.6)"];

function displayCategoryChart(data) {
    const ctx = document.getElementById("categoryChart");
    
    if (!ctx) {
        console.error("Canvas element not found");
        return;
    }

    // Destroy existing chart if it exists
    if (categoryChartInstance) {
        categoryChartInstance.destroy();
    }

    // Define colors for pie chart
    const colors = [
        "rgba(102, 126, 234, 0.6)",
        "rgba(255, 159, 64, 0.6)",
        "rgba(75, 192, 192, 0.6)",
        "rgba(255, 99, 132, 0.6)",
        "rgba(153, 102, 255, 0.6)"
    ];

    const borderColors = [
        "rgba(102, 126, 234, 1)",
        "rgba(255, 159, 64, 1)",
        "rgba(75, 192, 192, 1)",
        "rgba(255, 99, 132, 1)",
        "rgba(153, 102, 255, 1)"
    ];

    categoryChartInstance = new Chart(ctx, {
        type: "pie",
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: "Spending by Category (INR)",
                    data: data.values,
                    backgroundColor: colors.slice(0, data.labels.length),
                    borderColor: borderColors.slice(0, data.labels.length),
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: "bottom"
                }
            }
        }
    });
}

// Load data when page loads
document.addEventListener("DOMContentLoaded", function() {
    fetchEcoScore();
    fetchMonthlyExpenses();
    fetchCategoryData();
    
    // Add form submission listener
    const form = document.getElementById("transactionForm");
    if (form) {
        form.addEventListener("submit", handleFormSubmit);
    }
});

function handleFormSubmit(event) {
    event.preventDefault();
    
    const form = document.getElementById("transactionForm");
    const formData = new FormData(form);
    
    fetch(`${API_URL}/api/transactions`, {
        method: "POST",
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Failed to add transaction");
        }
        return response.json();
    })
    .then(data => {
        console.log("Transaction added:", data);
        // Refresh the main eco score from the server
        fetchEcoScore();
        // Clear form
        document.getElementById("transactionForm").reset();
        // Refresh charts and category data
        fetchMonthlyExpenses();
        fetchCategoryData();
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Error adding transaction. Please try again.");
    });
}

function uploadBulkCsv() {
    const fileInput = document.getElementById("csvUpload");
    const resultDisplay = document.getElementById("bulkImpactResult");
    const uploadButton = document.querySelector('.submit-btn[onclick="uploadBulkCsv()"]');

    uploadButton.disabled = true;
    uploadButton.textContent = "Analyzing... ⚙️";

    if (fileInput.files.length === 0) {
        alert("Please select a CSV file first.");
        return;
    }

    // Clear previous results and show loading state
    resultDisplay.innerHTML = "Analyzing...";
    if (bulkImpactChartInstance) {
        bulkImpactChartInstance.destroy();
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    fetch(`${API_URL}/api/upload-csv`, {
            method: "POST",
            body: formData,
        })
        .then((response) => {
            if (response.status === 401) {
                window.location.href = "/login.html";
                throw new Error("Unauthorized");
            }
            return response.json();
        })
        .then((data) => {
            if (data.error) {
                resultDisplay.innerHTML = `<span style="color:red">Error: ${data.error}</span>`;
            } else {
                // Update the main score display with the total impact from the CSV
                const scoreDisplay = document.getElementById('scoreDisplay');
                if (scoreDisplay) scoreDisplay.innerText = data.total_impact.toFixed(2);

                const pointsDisplay = document.getElementById('pointsDisplay');
                if (pointsDisplay) pointsDisplay.innerText = data.eco_points.toFixed(2);

                // Inject new HTML structure for results
                resultDisplay.innerHTML = `
                <div style="font-weight: bold; font-size: 1.2em;">
                    Total Impact: <span style="color:green">${data.total_impact.toFixed(2)}</span>
                </div>
                <div style="width: 100%; max-width: 400px; margin: 20px auto 0;">
                    <canvas id="bulkImpactChart"></canvas>
                </div>
            `;
                // Now render the chart
                displayBulkImpactChart(data.breakdown);
                updateCharts(data);
            }

            uploadButton.disabled = false;
            uploadButton.textContent = "Analyze CSV";
        })
        .catch((error) => {
            console.error("Error:", error);
            if (error.message !== "Unauthorized") {
                resultDisplay.textContent = "Error processing file.";
            }
        });


}

function displayBulkImpactChart(data) {
    const ctx = document.getElementById("bulkImpactChart");
    if (!ctx) return;

    const colors = ["rgba(255, 99, 132, 0.6)", "rgba(54, 162, 235, 0.6)", "rgba(255, 206, 86, 0.6)", "rgba(75, 192, 192, 0.6)", "rgba(153, 102, 255, 0.6)", "rgba(255, 159, 64, 0.6)"];


    bulkImpactChartInstance = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: data.labels,
            datasets: [{
                label: "Impact Breakdown",
                data: data.values,
                backgroundColor: colors,
                borderWidth: 1,
            }, ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: "top" },
                title: { display: true, text: "Impact Breakdown by Category" },
            },
        },
    });
}

function updateFileName() {
    const fileInput = document.getElementById('csvUpload');
    const fileNameDisplay = document.getElementById('csvFileName');
    if (fileInput.files.length > 0) {
        fileNameDisplay.textContent = fileInput.files[0].name;
    } else {
        fileNameDisplay.textContent = 'No file selected';
    }
}

function updateCharts(data) {
    // Update the Category Chart (Pie) using the existing function
    if (data.spending_breakdown) {
        displayCategoryChart(data.spending_breakdown);
    }

    // Update the Expenses Chart (Bar) to show Carbon Footprint by category
    const ctx = document.getElementById("expensesChart");
    if (!ctx) return;

    if (chartInstance) {
        chartInstance.destroy();
    }

    // Use the footprint breakdown for the bar chart
    const footprintData = data.breakdown || { labels: [], values: [] };

    chartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: footprintData.labels,
            datasets: [{
                label: "Carbon Footprint by Category",
                data: footprintData.values,
                backgroundColor: "rgba(102, 126, 234, 0.6)",
                borderColor: "rgba(102, 126, 234, 1)",
            borderWidth: 2,
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: true, position: "top" }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}
