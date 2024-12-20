from flask import Flask, render_template, jsonify
from datetime import datetime
import qrcode
import base64
import io
import logging
from queue_routes import queue_bp

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, template_folder="../Frontend/templates", static_folder="../Frontend/static")

app.register_blueprint(queue_bp, url_prefix='/queue')

# Home page to display the "You're Next" page
@app.route('/')
def home():
    return render_template('youre_next.html')  # Replace with your desired home page template

# Generate a static QR code with a fixed URL
@app.route('/queue/qr_code', methods=['GET'])
def generate_qr_code():
    try:
        # Define the static URL for the queue join endpoint
        static_url = 'https://cecb-128-76-247-146.ngrok-free.app/queue/join'

        # Create the QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(static_url)
        qr.make(fit=True)

        # Generate the QR code image
        img = qr.make_image(fill='black', back_color='white')

        # Save the QR code image to a BytesIO object
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr)
        img_byte_arr.seek(0)

        # Convert image to base64 for embedding in the webpage
        qr_code_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        # Render the scanqr.html template with the QR code image
        return render_template('scanqr.html', qr_code_image=qr_code_base64)

    except Exception as e:
        logging.error(f"Unexpected error in generate_qr_code: {str(e)}")
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

# Render a page to say "Have a Nice Day"
@app.route('/nice_day')
def nice_day():
    return render_template('nice_day.html')

# Render a dynamic queue status page
@app.route('/queue/dynamic', methods=['GET'])
def dynamic_queue():
    return render_template('dynamic_queue.html')

if __name__ == "__main__":
    app.run(debug=True)