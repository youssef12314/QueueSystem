    let currentQueueNumbers = []; // Track the current queue state

    function fetchQueueData() {
      $.get('/queue/people', function (data) {
        console.log('Fetched data:', data);
        const container = $('.queue-container');
        const newQueueNumbers = data.map(item => item.queue_number);

        // Handle people joining the queue
        newQueueNumbers.forEach(number => {
          if (!currentQueueNumbers.includes(number)) {
            console.log(`Person ${number} joining the queue.`);
            const personDiv = $(`
              <div class="person" data-queue-number="${number}">
                <img src="/static/images/person.png" alt="Person ${number}">
                <div class="queue-number">${number}</div>
              </div>
            `);
            container.append(personDiv);

            // Trigger show animation
            setTimeout(() => {
              personDiv.addClass('show');
              console.log(`Show animation triggered for person ${number}.`);
            }, 50); // Slight delay to ensure the DOM is updated
          }
        });

        // Handle people leaving the queue
        currentQueueNumbers.forEach(number => {
          if (!newQueueNumbers.includes(number)) {
            console.log(`Person ${number} leaving the queue.`);
            const personDiv = container.find(`.person[data-queue-number="${number}"]`);
            personDiv.addClass('hide'); // Trigger hide animation

            // Remove from DOM after animation
            setTimeout(() => {
              personDiv.remove();
              console.log(`Person ${number} removed from DOM.`);
            }, 1000); // Matches the CSS transition duration
          }
        });

        // Update the current queue state
        currentQueueNumbers = newQueueNumbers;
        console.log('Updated queue state:', currentQueueNumbers);

        // Update the display for the first queue number
        if (currentQueueNumbers.length > 0) {
          $('.queue-number-display').text(currentQueueNumbers[0]);
        } else {
          $('.queue-number-display').text('');
        }
      }).fail(function (error) {
        console.error('Error fetching queue data:', error);
      });
    }

    // Fetch queue data every 2 seconds
    setInterval(fetchQueueData, 2000);

    // Initial fetch on page load
    fetchQueueData();
