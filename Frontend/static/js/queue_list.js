function fetchQueueData() {
    $.get('/queue/people', function(data) {
        let tbody = $('#queue-table tbody');
        tbody.empty();  

        
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


setInterval(fetchQueueData, 2000);

fetchQueueData();
