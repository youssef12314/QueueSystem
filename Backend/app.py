from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for, make_response
import mysql.connector
import qrcode
import io
from datetime import datetime
import logging
import uuid
from datetime import datetime, timedelta
import time
import base64




logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Initialize database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="X94nunecayjnc",
    database="queue_management"
)

# Home page to display the QR code
@app.route('/')
def home():
    return render_template('youre_next.html')  # Page for scanning the QR code


# Generate a static QR code with a fixed URL
@app.route('/queue/qr_code', methods=['GET'])
def generate_qr_code():
    try:
        # Define the static URL
        static_url = 'https://d53d-128-76-247-146.ngrok-free.app/queue/join'

        # Create the QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(static_url)
        qr.make(fit=True)

        # Generate the QR code image
        img = qr.make_image(fill='black', back_color='white')

        # Save the QR code to a BytesIO object for response
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr)
        img_byte_arr.seek(0)

        # Convert image to base64
        qr_code_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        # Render the scanqr.html page and pass the base64-encoded image
        return render_template('scanqr.html', qr_code_image=qr_code_base64)

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/queue/join', methods=['GET'])
def join_queue():
    try:
        session_id = request.cookies.get('session_id')

        if not session_id:
            session_id = str(uuid.uuid4())

        cursor = db.cursor(dictionary=True)

        # Check if the user is already in the queue
        cursor.execute("SELECT queue_number FROM customers WHERE session_id = %s", (session_id,))
        existing_customer = cursor.fetchone()

        if existing_customer:
            queue_number = existing_customer['queue_number']
        else:
            # Fetch the last assigned queue number
            cursor.execute("SELECT MAX(queue_number) AS last_queue_number FROM customers")
            result = cursor.fetchone()
            last_queue_number = result['last_queue_number'] or 0

            # Calculate the new queue number (reset after 99)
            new_queue_number = (last_queue_number % 99) + 1

            # Format the queue number to always be two digits
            formatted_queue_number = f"{new_queue_number:02d}"

            # Insert the new customer with the assigned formatted queue number
            cursor.execute(
                "INSERT INTO customers (queue_number, session_id, joined_at, last_active) VALUES (%s, %s, %s, %s)",
                (formatted_queue_number, session_id, datetime.now(), datetime.now())
            )
            db.commit()
            queue_number = formatted_queue_number

        cursor.close()

        # Set the session ID in the user's cookie
        response = make_response(render_template('mobile.html', queue_number=queue_number))
        response.set_cookie('session_id', session_id, max_age=3600, httponly=True)
        return response

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    
# API route to fetch queue status (optional but helpful for API integration)
@app.route('/api/queue_status', methods=['GET'])
def queue_status():
    try:
        cursor = db.cursor()
        cursor.execute("SELECT queue_number, joined_at FROM customers ORDER BY queue_number")
        customers = cursor.fetchall()
        cursor.close()

        return jsonify([
            {"queue_number": customer[0], "joined_at": customer[1].strftime('%Y-%m-%d %H:%M:%S')}
            for customer in customers
        ])

    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
    

 
@app.route('/queue/list', methods=['GET'])
def view_queue():
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT queue_number, joined_at FROM customers ORDER BY queue_number ASC")
        customers = cursor.fetchall()
        cursor.close()

        # Render the queue list page
        return render_template('queue_list.html', customers=customers)

    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route('/queue/people', methods=['GET'])
def get_queue():
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT queue_number, joined_at FROM customers ORDER BY joined_at ASC")
        customers = cursor.fetchall()
        cursor.close()

        # Add current_position based on order and format queue_number with leading zero
        queue_data = [
            {
                "queue_number": f"{customer['queue_number']:02d}",  # Format the queue number to 2 digits
                "joined_at": customer["joined_at"].strftime('%Y-%m-%d %H:%M:%S'),
                "current_position": idx + 1  # Position starts at 1
            }
            for idx, customer in enumerate(customers)
        ]

        return jsonify(queue_data)

    except mysql.connector.Error as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    

def remove_inactive_users():
    while True:
        try:
            cursor = db.cursor()
            threshold_time = datetime.now() - timedelta(minutes=5)
            
            # Remove inactive users
            cursor.execute("DELETE FROM customers WHERE last_active < %s", (threshold_time,))
            db.commit()
            cursor.close()

            # Reorder the queue after removing inactive users
            reorder_queue()

        except mysql.connector.Error as e:
            logging.error(f"Database error in remove_inactive_users: {e}")

        time.sleep(30)  # Sleep for 60 seconds before running again

@app.route('/queue/heartbeat', methods=['POST'])
def heartbeat():
    session_id = request.cookies.get('session_id')
    if session_id:
        cursor = db.cursor()
        cursor.execute("UPDATE customers SET last_active = %s WHERE session_id = %s", (datetime.now(), session_id))
        db.commit()
        cursor.close()
        return jsonify({"message": "Heartbeat updated."})
    return jsonify({"error": "No session ID found."}), 400

def reorder_queue():
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM customers ORDER BY joined_at ASC")
        customers = cursor.fetchall()

        for index, customer in enumerate(customers):
            new_queue_number = (index % 99) + 1  # Reset after 99
            formatted_queue_number = f"{new_queue_number:02d}"
            cursor.execute("UPDATE customers SET queue_number = %s WHERE id = %s", (formatted_queue_number, customer[0]))

        db.commit()
        cursor.close()
        logging.info("Queue reordered successfully.")

    except mysql.connector.Error as e:
        logging.error(f"Database error in reorder_queue: {e}")


@app.route('/queue/leave', methods=['POST'])
def leave_queue():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return redirect(url_for('home'))

        cursor = db.cursor()
        
        # Delete the record from the 'number' table
        cursor.execute("DELETE FROM customers WHERE session_id = %s", (session_id,))
        db.commit()
        cursor.close()

        # Update positions (you may need to adapt this based on your logic)
        reorder_positions()

        # Clear session cookie and redirect to 'nice_day' page
        response = make_response(redirect(url_for('nice_day')))
        response.delete_cookie('session_id')
        return response

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500
    

@app.route('/queue/my_status', methods=['GET'])
def my_status():
    try:
        session_id = request.cookies.get('session_id')

        if not session_id:
            return jsonify({"error": "No session ID found."}), 400  # Return a JSON error

        cursor = db.cursor(dictionary=True)

        # Get the customer's queue details
        cursor.execute("""
            SELECT queue_number, 
                   (SELECT COUNT(*) FROM customers WHERE queue_number <= c.queue_number) AS dynamic_position
            FROM customers c 
            WHERE session_id = %s
        """, (session_id,))
        result = cursor.fetchone()

        if result:
            queue_number = result['queue_number']
            dynamic_position = result['dynamic_position']

            # Calculate the estimated waiting time based on the total service time for customers ahead
            cursor.execute("""
                SELECT SUM(service_time) AS total_waiting_time
                FROM customers
                WHERE queue_number < %s
            """, (queue_number,))
            total_waiting_time = cursor.fetchone()['total_waiting_time'] or 0

            # Now calculate the average estimated wait time for the dynamic position
            estimated_waiting_time = total_waiting_time / max(dynamic_position, 1)  # Avoid division by 0

            cursor.close()

            # Ensure queue number is formatted with a leading zero
            formatted_queue_number = f"{queue_number:02d}"
            return jsonify({
                "queue_number": formatted_queue_number,
                "dynamic_position": dynamic_position,
                "estimated_waiting_time": estimated_waiting_time
            })
        else:
            return jsonify({"error": "Not in queue", "redirect": "/queue/youre_next"}), 404

    except mysql.connector.Error as err:
        logging.error(f"Database error in my_status: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500



@app.route('/nice_day')
def nice_day():
    return render_template('nice_day.html')

def reorder_positions():
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM customers ORDER BY joined_at ASC")
        customers = cursor.fetchall()

        # Reassign dynamic positions
        for index, customer in enumerate(customers):
            cursor.execute("UPDATE customers SET dynamic_position = %s WHERE id = %s", (index + 1, customer[0]))

        db.commit()
        cursor.close()
        logging.info("Queue positions updated successfully.")

    except mysql.connector.Error as e:
        logging.error(f"Database error in reorder_positions: {e}")


@app.route('/queue/next', methods=['POST'])
def next_customer():
    try:
        # Get the first customer in the queue (position 1)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, queue_number, session_id FROM customers ORDER BY joined_at ASC LIMIT 1")
        first_customer = cursor.fetchone()

        if first_customer:
            # Remove the first customer from the queue
            cursor.execute("DELETE FROM customers WHERE id = %s", (first_customer['id'],))
            db.commit()

            # Reassign dynamic positions for the remaining customers
            reorder_positions()

            # Set session cookie for the next customer
            response = make_response(redirect(url_for('youre_next')))
            response.set_cookie('session_id', first_customer['session_id'], max_age=3600, httponly=True)
            return response

        else:
            return jsonify({"error": "No customers in the queue."}), 404

    except mysql.connector.Error as err:
        logging.error(f"Database error in next_customer: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    

@app.route('/queue/youre_next', methods=['GET'])
def youre_next():
    try:
        session_id = request.cookies.get('session_id')

        if not session_id:
            return redirect(url_for('home'))  # If session_id doesn't exist, redirect to the home page

        # Check if the session ID exists in the database
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT queue_number FROM customers WHERE session_id = %s", (session_id,))
        customer = cursor.fetchone()
        cursor.close()

        if customer:
            # Render the 'youre_next.html' page
            return render_template('youre_next.html')
        else:
            return redirect(url_for('home'))  # If session ID doesn't match any customer, redirect to home

    except mysql.connector.Error as err:
        logging.error(f"Database error in youre_next: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500

@app.route('/queue/dynamic', methods=['GET'])
def dynamic_queue():
    return render_template('dynamic_queue.html')

if __name__ == "__main__":
    app.run(debug=True)