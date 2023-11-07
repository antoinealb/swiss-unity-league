// Debounce function to limit the rate at which the suggestions are fetched
function debounce(func, wait) {
    let timeout;
    return function () {
        const context = this, args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('id_player_name');
    const dropdown = document.getElementById('autocomplete-dropdown');
    const url = input.getAttribute('data-autocomplete-url');

    const fetchSuggestions = debounce(function () {
        fetch(`${url}?search_name=${input.value}`)
            .then(response => response.json())
            .then(data => {
            dropdown.innerHTML = ''; // Clear existing dropdown items
            data.forEach((item) => {
                // Create new dropdown item for each suggestion
                const option = document.createElement('a');
                option.className = 'dropdown-item';
                option.href = '#';
                option.textContent = item.name;
                option.addEventListener('click', function (e) {
                    e.preventDefault();
                    input.value = item.name; // Set input value
                    dropdown.style.display = 'none'; // Hide dropdown
                });
                dropdown.appendChild(option);
            });
            // Show dropdown only if there are suggestions
            dropdown.style.display = data.length ? 'block' : 'none';
        });
    }, 500); // 500ms debounce time

    // Make request when user types in input field
    input.addEventListener('input', fetchSuggestions);

    // Hide dropdown when input loses focus
    input.addEventListener('blur', function () {
        setTimeout(() => {
            dropdown.style.display = 'none';
        }, 200);
    });
});
