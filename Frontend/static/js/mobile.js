async function fetchQueueStatus() {
    try {
        const response = await fetch('/queue/my_status');

        if (response.ok) {
            const data = await response.json();
            console.log('Fetched data:', data); // Debug log

            if (data.queue_number && data.dynamic_position !== undefined) {
                // Update queue number and position
                document.getElementById('queue-number').textContent = data.queue_number;
                document.getElementById('queue-position').textContent = data.dynamic_position;

                // Redirect to "youre_next.html" if position is 1
                if (data.dynamic_position === 1) {
                    window.location.href = '/queue/youre_next';
                    return; // Exit the function to avoid further updates
                }

                // Update the estimated waiting time, default to "Calculating..." if not available
                let estimatedWaitingTime = data.estimated_waiting_time;

                if (estimatedWaitingTime !== undefined) {
                    // Round to the nearest whole number to remove decimal places
                    estimatedWaitingTime = Math.round(estimatedWaitingTime);
                } else {
                    estimatedWaitingTime = "Calculating...";
                }

                document.getElementById('waiting-time').textContent = estimatedWaitingTime;
            } else if (data.error) {
                alert(data.error);
                if (data.redirect) {
                    window.location.href = data.redirect;  // Redirect to the new page
                } else {
                    window.location.href = '/'; // Fallback, just in case
                }
            }
        } else {
            const text = await response.text();
            console.log('Non-JSON response:', text);
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Error fetching queue status:', error);
    }
}

        // Poll the API every 1 second to check for updates
        setInterval(fetchQueueStatus, 1000);

        // Initial fetch on page load
        fetchQueueStatus();