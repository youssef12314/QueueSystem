async function fetchQueueStatus() {
    try {
        const response = await fetch('/queue/my_status');

        if (response.ok) {
            const data = await response.json();
            console.log('Fetched data:', data); 

            if (data.queue_number && data.dynamic_position !== undefined) {
                
                document.getElementById('queue-number').textContent = data.queue_number;
                document.getElementById('queue-position').textContent = data.dynamic_position;

                
                if (data.dynamic_position === 1) {
                    window.location.href = '/queue/youre_next';
                    return; 
                }

                
                let estimatedWaitingTime = data.estimated_waiting_time;

                if (estimatedWaitingTime !== undefined) {
                    
                    estimatedWaitingTime = Math.round(estimatedWaitingTime);
                } else {
                    estimatedWaitingTime = "Calculating...";
                }

                document.getElementById('waiting-time').textContent = estimatedWaitingTime;
            } else if (data.error) {
                alert(data.error);
                if (data.redirect) {
                    window.location.href = data.redirect;  
                } else {
                    window.location.href = '/'; 
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

        
        setInterval(fetchQueueStatus, 1000);

       
        fetchQueueStatus();
