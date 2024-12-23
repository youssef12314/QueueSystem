function fetchQueueData() {
    $.get('/queue/people', function(data) {
        let tbody = $('#queue-table tbody');
        tbody.empty();  // Clear existing rows

        // Loop through the queue data and add it to the table
        data.forEach(function(item) {
            let row = `<tr>
                <td>${item.queue_number}</td>
                <td>${item.current_position}</td>
                <td>${item.joined_at}</td>
            </tr>`;
            tbody.append(row);
        });
    });
}
$('#next-button').click(function() {
    $.post('/queue/next', function() {
        // After successfully processing, update the queue data
        fetchQueueData();
    }).fail(function(xhr, status, error) {
        try {
            let errorMessage = xhr.responseJSON ? xhr.responseJSON.error : "Unknown error occurred";
            alert('Error: ' + errorMessage);
        } catch (e) {
            alert('Error: ' + error);
        }
    });
});

// Fetch queue data every 2 seconds
setInterval(fetchQueueData, 2000);

// Initial fetch on page load
fetchQueueData();