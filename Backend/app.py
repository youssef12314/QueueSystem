from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
from mysql.connector import pooling, Error as MySQLError
from datetime import datetime, timedelta
import qrcode
import base64
import uuid
import io
import logging
import time
import threading



logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

# Initialize database connection
connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    host="localhost",
    user="root",
    password="X94nunecayjnc",
    database="queue_management"
)

def get_db_connection():
    try:
        connection = connection_pool.get_connection()
        return connection
    except MySQLError as err:
        logging.error(f"Error getting connection from pool: {err}")
        raise err

# Home page to display the QR code
@app.route('/')
def home():
    return render_template('youre_next.html')  # Page for scanning the QR code


# Generate a static QR code with a fixed URL
@app.route('/queue/qr_code', methods=['GET'])
def generate_qr_code():
    try:
        # Define the static URL
        static_url = 'https://75c8-128-76-247-146.ngrok-free.app/queue/join'

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
            session_id = str(uuid.uuid4())  # Generate new session ID if none exists

        # Get DB connection using context manager to ensure proper cleanup
        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
            if db is None:
                return jsonify({"error": "Database connection failed"}), 500

            # Check if the user is already in the queue
            cursor.execute("SELECT queue_number FROM customers WHERE session_id = %s", (session_id,))
            existing_customer = cursor.fetchone()

            if existing_customer:
                # Customer is already in the queue
                queue_number = existing_customer['queue_number']
            else:
                # If not in queue, assign a new queue number
                cursor.execute("SELECT MAX(queue_number) AS last_queue_number FROM customers")
                result = cursor.fetchone()
                last_queue_number = result['last_queue_number'] or 0

                # Increment the queue number, reset after 99
                new_queue_number = (last_queue_number % 99) + 1
                formatted_queue_number = f"{new_queue_number:02d}"

                # Insert the new customer into the queue
                cursor.execute(
                    "INSERT INTO customers (queue_number, session_id, joined_at, last_active) VALUES (%s, %s, %s, %s)",
                    (formatted_queue_number, session_id, datetime.now(), datetime.now())
                )
                db.commit()
                queue_number = formatted_queue_number

        # Create a response and set the session_id cookie for 1 hour
        response = make_response(render_template('mobile.html', queue_number=queue_number))
        response.set_cookie('session_id', session_id, max_age=3600, httponly=True)
        return response

    except MySQLError as err:
        logging.error(f"Database error in join_queue: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error in join_queue: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
    
# API route to fetch queue status (optional but helpful for API integration)
@app.route('/api/queue_status', methods=['GET'])
def queue_status():
    try:
        with get_db_connection() as db, db.cursor() as cursor:
            cursor.execute("SELECT queue_number, joined_at FROM customers ORDER BY queue_number")
            customers = cursor.fetchall()

        return jsonify([
            {
                "queue_number": customer[0],
                "joined_at": customer[1].strftime('%Y-%m-%d %H:%M:%S')
            }
            for customer in customers
        ])

    except MySQLError as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

 
@app.route('/queue/list', methods=['GET'])
def view_queue():
    try:
        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT queue_number, joined_at FROM customers ORDER BY queue_number ASC")
            customers = cursor.fetchall()
        return render_template('queue_list.html', customers=customers)
    except MySQLError as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500

@app.route('/queue/people', methods=['GET'])
def get_queue():
    try:
        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT queue_number, joined_at FROM customers ORDER BY joined_at ASC")
            customers = cursor.fetchall()

        # Add current_position based on order and format queue_number with leading zero
        queue_data = [
            {
                "queue_number": f"{customer['queue_number']:02d}",
                "joined_at": customer["joined_at"].strftime('%Y-%m-%d %H:%M:%S'),
                "current_position": idx + 1
            }
            for idx, customer in enumerate(customers)
        ]

        return jsonify(queue_data)

    except MySQLError as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    

def remove_inactive_users():
    while True:
        try:
            with get_db_connection() as db, db.cursor() as cursor:
                threshold_time = datetime.now() - timedelta(minutes=5)
                cursor.execute("DELETE FROM customers WHERE last_active < %s", (threshold_time,))
                db.commit()
            time.sleep(30)
        except MySQLError as e:
            logging.error(f"Database error in remove_inactive_users: {e}")
            
@app.route('/queue/heartbeat', methods=['POST'])
def heartbeat():
    try:
        session_id = request.cookies.get('session_id')
        if session_id:
            with get_db_connection() as db, db.cursor() as cursor:
                cursor.execute(
                    "UPDATE customers SET last_active = %s WHERE session_id = %s",
                    (datetime.now(), session_id)
                )
                db.commit()
            return jsonify({"message": "Heartbeat updated."})

        return jsonify({"error": "No session ID found."}), 400

    except MySQLError as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500

def reorder_queue():
    try:
        with get_db_connection() as db, db.cursor() as cursor:
            cursor.execute("SELECT id FROM customers ORDER BY joined_at ASC")
            customers = cursor.fetchall()

            for index, customer in enumerate(customers):
                new_queue_number = (index % 99) + 1
                formatted_queue_number = f"{new_queue_number:02d}"
                cursor.execute(
                    "UPDATE customers SET queue_number = %s WHERE id = %s",
                    (formatted_queue_number, customer[0])
                )

            db.commit()
            logging.info("Queue reordered successfully.")

    except MySQLError as e:
        logging.error(f"Database error in reorder_queue: {e}")


@app.route('/queue/leave', methods=['POST'])
def leave_queue():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return redirect(url_for('home'))

        with get_db_connection() as db, db.cursor() as cursor:
            cursor.execute("DELETE FROM customers WHERE session_id = %s", (session_id,))
            db.commit()

        response = make_response(redirect(url_for('nice_day')))
        response.delete_cookie('session_id')
        return response

    except MySQLError as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    

@app.route('/queue/my_status', methods=['GET'])
def my_status():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({"error": "No session ID found."}), 400

        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
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
                
                formatted_queue_number = f"{queue_number:02d}"

                return jsonify({
                    "queue_number": formatted_queue_number,
                    "dynamic_position": dynamic_position,
                    "estimated_waiting_time": estimated_waiting_time
                })
            else:
                return jsonify({"error": "Not in queue"}), 404

    except MySQLError as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500


@app.route('/nice_day')
def nice_day():
    return render_template('nice_day.html')

def reorder_positions():
    try:
        with get_db_connection() as db, db.cursor() as cursor:
            cursor.execute("SELECT id FROM customers ORDER BY joined_at ASC")
            customers = cursor.fetchall()

            for index, customer in enumerate(customers):
                cursor.execute(
                    "UPDATE customers SET dynamic_position = %s WHERE id = %s",
                    (index + 1, customer[0])
                )

            db.commit()
            logging.info("Queue positions updated successfully.")

    except MySQLError as e:
        logging.error(f"Database error in reorder_positions: {e}")

@app.route('/queue/next', methods=['POST'])
def next_customer():
    try:
        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
            # Get the first customer in the queue
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

        return jsonify({"error": "No customers in the queue."}), 404

    except MySQLError as err:
        logging.error(f"Database error in next_customer: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    

@app.route('/queue/youre_next', methods=['GET'])
def youre_next():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return redirect(url_for('home'))

        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT queue_number FROM customers WHERE session_id = %s", (session_id,))
            if cursor.fetchone():
                return render_template('youre_next.html')
        return redirect(url_for('home'))

    except MySQLError as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500

@app.route('/queue/dynamic', methods=['GET'])
def dynamic_queue():
    return render_template('dynamic_queue.html')

if __name__ == "__main__":
    app.run(debug=True)