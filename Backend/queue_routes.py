from flask import Blueprint, request, jsonify, render_template, redirect, url_for, make_response
from mysql.connector import Error as MySQLError
from datetime import datetime
import uuid
import logging
from db import get_db_connection

queue_bp = Blueprint('queue', __name__)

@queue_bp.route('/join', methods=['GET'])
def join_queue():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())

        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
            # Check if the user is already in the queue
            cursor.execute("SELECT queue_number FROM customers WHERE session_id = %s", (session_id,))
            existing_customer = cursor.fetchone()

            if existing_customer:
                queue_number = existing_customer['queue_number']
            else:
                cursor.execute("SELECT MAX(queue_number) AS last_queue_number FROM customers")
                last_queue_number = cursor.fetchone()['last_queue_number'] or 0
                new_queue_number = last_queue_number + 1
                formatted_queue_number = f"{new_queue_number:02d}"

                cursor.execute(
                    "INSERT INTO customers (queue_number, session_id, joined_at, last_active) VALUES (%s, %s, %s, %s)",
                    (formatted_queue_number, session_id, datetime.now(), datetime.now())
                )
                db.commit()
                queue_number = formatted_queue_number

        response = make_response(render_template('mobile.html', queue_number=queue_number))

        # Debug URL resolution
        try:
            leave_queue_url = url_for('queue.leave_queue', _external=True)
            logging.debug(f"Resolved leave_queue URL: {leave_queue_url}")
        except Exception as e:
            logging.error(f"Error resolving leave_queue URL: {e}")
            raise

        response.set_cookie('leave_queue', leave_queue_url)
        response.set_cookie('session_id', session_id, max_age=3600, httponly=True)

        return response

    except MySQLError as err:
        logging.error(f"Database error in join_queue: {err}")
        return jsonify({"error": "Database error."}), 500
    except Exception as e:
        logging.error(f"Unexpected error in join_queue: {str(e)}")
        return jsonify({"error": "Unexpected error."}), 500

@queue_bp.route('/api/queue_status', methods=['GET'])
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
        return jsonify({"error": "Database error."}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Unexpected error."}), 500


@queue_bp.route('/list', methods=['GET'])
def view_queue():
    try:
        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT queue_number, joined_at FROM customers ORDER BY queue_number ASC")
            customers = cursor.fetchall()
        return render_template('queue_list.html', customers=customers)
    except MySQLError as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": "Database error."}), 500


@queue_bp.route('/leave', methods=['POST'])
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
        return jsonify({"error": "Database error."}), 500


@queue_bp.route('/heartbeat', methods=['POST'])
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
        return jsonify({"error": "Database error."}), 500


@queue_bp.route('/my_status', methods=['GET'])
def my_status():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({"error": "No session ID found."}), 400

        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
            cursor.execute(
                """
                SELECT queue_number, 
                       (SELECT COUNT(*) FROM customers WHERE queue_number <= c.queue_number) AS dynamic_position
                FROM customers c 
                WHERE session_id = %s
                """, (session_id,))
            result = cursor.fetchone()

            if result:
                queue_number = result['queue_number']
                dynamic_position = result['dynamic_position']
                
                # Calculate the total waiting time for customers ahead
                cursor.execute("""
                    SELECT SUM(service_time) AS total_waiting_time
                    FROM customers
                    WHERE queue_number < %s
                """, (queue_number,))
                total_waiting_time = cursor.fetchone()['total_waiting_time'] or 0

                # Calculate the average estimated waiting time per dynamic position
                estimated_waiting_time = total_waiting_time / max(dynamic_position, 1)  # Avoid division by 0
                
                return jsonify({
                    "queue_number": f"{queue_number:02d}",
                    "dynamic_position": dynamic_position,
                    "estimated_waiting_time": estimated_waiting_time
                })
            else:
                return jsonify({"error": "Not in queue."}), 404

    except MySQLError as err:
        logging.error(f"Database error: {err}")
        return jsonify({"error": f"Database error: {err}"}), 500
    

@queue_bp.route('/people', methods=['GET'])
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
    

@queue_bp.route('/next', methods=['POST'])
def next_customer():
    try:
        with get_db_connection() as db, db.cursor(dictionary=True) as cursor:
            # Get the first customer in the queue
            cursor.execute("SELECT id, queue_number, session_id FROM customers ORDER BY queue_number ASC LIMIT 1 FOR UPDATE")
            first_customer = cursor.fetchone()

            if not first_customer:
                return jsonify({"error": "No customers in the queue."}), 404

            # Remove the first customer
            cursor.execute("DELETE FROM customers WHERE id = %s", (first_customer['id'],))
            db.commit()

            # No need to reorder queue numbers if they're not reused
            return jsonify({"message": f"Customer {first_customer['queue_number']} has been served."})
    except MySQLError as err:
        logging.error(f"Database error in next_customer: {err}")
        return jsonify({"error": "Database error."}), 500
    except Exception as e:
        logging.error(f"Unexpected error in next_customer: {e}")
        return jsonify({"error": "Unexpected error."}), 500

    

def reorder_positions(db, cursor):
    try:
        cursor.execute("SELECT id FROM customers ORDER BY queue_number ASC")
        customers = cursor.fetchall()
        logging.debug(f"Customers before reordering: {customers}")

        for index, customer in enumerate(customers):
            new_queue_number = index + 1  # Start from 1
            cursor.execute(
                "UPDATE customers SET queue_number = %s WHERE id = %s",
                (new_queue_number, customer['id'])
            )

        db.commit()
        logging.info("Queue positions updated successfully.")
    except MySQLError as e:
        logging.error(f"Database error in reorder_positions: {e}")
        db.rollback()
        raise


@queue_bp.route('/youre_next', methods=['GET'])
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
        return jsonify({"error": "Database error."}), 500