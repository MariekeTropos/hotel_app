from flask import Flask, render_template_string, request, redirect, url_for, Response
import datetime
import csv
from io import StringIO

# Initialize Flask app
app = Flask(__name__)

# Define room types and their corresponding price per night
ROOM_TYPES = {
    'Single': 50,
    'Double': 80,
    'Suite': 120
}

class Hotel:
    """
    A simple Hotel management class to handle bookings, checkouts,
    and track room availability and guest information.
    """
    def __init__(self, total_rooms):
        self.total_rooms = total_rooms
        self.available_rooms = total_rooms
        self.guests = {}  # room_number -> guest_info dict
        self.history = []  # list of checked-out guests
        self.room_type_count = {key: 0 for key in ROOM_TYPES}

    def check_in(self, name, email, phone, room_type, nights, special_requests):
        """
        Assign a room to a new guest with their details.
        Calculates total cost based on room type and nights.
        Adds timestamp and optional special requests.
        """
        if self.available_rooms == 0:
            return None

        room_number = self.total_rooms - self.available_rooms + 1
        price_per_night = ROOM_TYPES.get(room_type, 50)
        total_cost = price_per_night * nights
        check_in_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.guests[room_number] = {
            'name': name,
            'email': email,
            'phone': phone,
            'room_type': room_type,
            'nights': nights,
            'total_cost': total_cost,
            'check_in_date': check_in_date,
            'special_requests': special_requests
        }
        self.available_rooms -= 1
        self.room_type_count[room_type] += 1
        return room_number

    def check_out(self, room_number):
        """
        Remove guest info from a room and free it up.
        Archive guest info in history.
        """
        if room_number in self.guests:
            guest = self.guests.pop(room_number)
            guest['room_number'] = room_number
            guest['check_out_date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.history.append(guest)
            self.available_rooms += 1
            self.room_type_count[guest['room_type']] -= 1
            return guest
        return None

    def get_guest_list(self):
        return self.guests

    def get_available_rooms(self):
        return self.available_rooms

    def get_available_by_type(self):
        result = {}
        for rtype in ROOM_TYPES:
            total = list(ROOM_TYPES).index(rtype) + 1  # dummy count by order
            result[rtype] = total - self.room_type_count[rtype]
        return result

    def get_history(self):
        return self.history

hotel = Hotel(total_rooms=5)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Hotel Management</title>
</head>
<body>
    <h1>Hotel Management System</h1>
    <h2>Available Rooms: {{ available }}</h2>
    <h4>By Room Type:</h4>
    <ul>
        {% for type, count in available_by_type.items() %}
            <li>{{ type }}: {{ count }}</li>
        {% endfor %}
    </ul>

    <h3>Book a Room</h3>
    <form action="/checkin" method="post">
        Name: <input type="text" name="name" required><br>
        Email: <input type="email" name="email" required><br>
        Phone: <input type="text" name="phone" required><br>
        Room Type:
        <select name="room_type">
            {% for type in room_types %}
                <option value="{{ type }}">{{ type }} (${{ room_types[type] }}/night)</option>
            {% endfor %}
        </select><br>
        Nights: <input type="number" name="nights" min="1" required><br>
        Special Requests: <input type="text" name="special_requests"><br>
        <input type="submit" value="Check In">
    </form>

    <h3>Check Out</h3>
    <form action="/checkout" method="post">
        Room Number: <input type="number" name="room" required>
        <input type="submit" value="Check Out">
    </form>

    <h3>Guest List</h3>
    <ul>
        {% for room, guest in guests.items() %}
            <li>
                <strong>Room {{ room }}:</strong> {{ guest.name }} ({{ guest.room_type }} - {{ guest.nights }} nights - ${{ guest.total_cost }})<br>
                Email: {{ guest.email }}, Phone: {{ guest.phone }}<br>
                Check-in: {{ guest.check_in_date }}<br>
                {% if guest.special_requests %}Special Requests: {{ guest.special_requests }}{% endif %}
            </li>
        {% endfor %}
    </ul>

    <h3>Check-out History</h3>
    <a href="/export">Download CSV</a>
    <ul>
        {% for guest in history %}
            <li>
                <strong>Room {{ guest.room_number }}:</strong> {{ guest.name }} ({{ guest.room_type }})<br>
                Stay: {{ guest.nights }} nights, ${{ guest.total_cost }}<br>
                Checked in: {{ guest.check_in_date }}, Checked out: {{ guest.check_out_date }}
            </li>
        {% endfor %}
    </ul>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, 
                                  available=hotel.get_available_rooms(),
                                  available_by_type=hotel.get_available_by_type(),
                                  guests=hotel.get_guest_list(),
                                  history=hotel.get_history(),
                                  room_types=ROOM_TYPES)

@app.route('/checkin', methods=['POST'])
def checkin():
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    room_type = request.form['room_type']
    nights = int(request.form['nights'])
    special_requests = request.form.get('special_requests', '')
    hotel.check_in(name, email, phone, room_type, nights, special_requests)
    return redirect(url_for('index'))

@app.route('/checkout', methods=['POST'])
def checkout():
    try:
        room = int(request.form['room'])
        hotel.check_out(room)
    except ValueError:
        pass
    return redirect(url_for('index'))

@app.route('/export')
def export():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Room Number', 'Name', 'Email', 'Phone', 'Room Type', 'Nights', 'Total Cost', 'Check-in', 'Check-out'])
    for guest in hotel.get_history():
        writer.writerow([
            guest['room_number'], guest['name'], guest['email'], guest['phone'],
            guest['room_type'], guest['nights'], guest['total_cost'],
            guest['check_in_date'], guest['check_out_date']
        ])
    output.seek(0)
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=guest_history.csv'})

if __name__ == '__main__':
    app.run(debug=True)