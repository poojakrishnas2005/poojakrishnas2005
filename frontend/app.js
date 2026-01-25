const API_URL = "http://localhost:5000";

let chartInstance = null;
let categoryChartInstance = null;

function fetchEcoScore() {
    const scoreDisplay = document.getElementById("scoreDisplay");
    scoreDisplay.textContent = "Loading...";
    
    fetch(`${API_URL}/eco-score`)
        .then(response => {
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            return response.json();
        })
        .then(data => {
            scoreDisplay.textContent = data.eco_score;
            scoreDisplay.classList.add("score-loaded");
        })
        .catch(error => {
            console.error("Error:", error);
            scoreDisplay.textContent = "Error loading score";
            scoreDisplay.classList.add("error");
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
    fetch(`${API_URL}/api/category-data`)
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
                    label: "Carbon Impact",
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
    
    const itemName = document.getElementById("itemName").value;
    const amount = document.getElementById("amount").value;
    const category = document.getElementById("category").value;
    
    const transactionData = {
        item_name: itemName,
        amount_in_inr: parseFloat(amount),
        category: category,
        carbon_impact: 0.0
    };
    
    fetch(`${API_URL}/api/transactions`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(transactionData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Failed to add transaction");
        }
        return response.json();
    })
    .then(data => {
        console.log("Transaction added:", data);
        // Clear form
        document.getElementById("transactionForm").reset();
        // Refresh eco-score, charts, and category data
        fetchEcoScore();
        fetchMonthlyExpenses();
        fetchCategoryData();
        alert("Transaction added successfully!");
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Error adding transaction. Please try again.");
    });
}

