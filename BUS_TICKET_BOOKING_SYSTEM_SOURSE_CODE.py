# 0. Install Gradio (if not already installed in Colab)
# !pip install gradio

# 1. Imports & DB setup
import sqlite3
import gradio as gr

# connect to a file-based SQLite DB
conn = sqlite3.connect("bus_booking.db", check_same_thread=False)
cursor = conn.cursor()

# create tables if they don't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS buses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bus_name TEXT NOT NULL UNIQUE,
    from_city TEXT NOT NULL,
    to_city TEXT NOT NULL,
    total_seats INTEGER NOT NULL CHECK(total_seats > 0)
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passenger_name TEXT NOT NULL,
    bus_id INTEGER NOT NULL,
    travel_date TEXT NOT NULL,
    seat_number INTEGER NOT NULL,
    FOREIGN KEY(bus_id) REFERENCES buses(id),
    UNIQUE(bus_id, travel_date, seat_number)
)
''')
conn.commit()

# 2. Admin: add a new bus
# def add_bus(bus_name, from_city, to_city, total_seats):
#     if not (bus_name and from_city and to_city and total_seats):
#         return "❌ All fields are required."
#     try:
#         seats = int(total_seats)
#         if seats <= 0:
#             return "❌ Total seats must be a positive integer."
#         cursor.execute(
#             "INSERT INTO buses (bus_name, from_city, to_city, total_seats) VALUES (?, ?, ?, ?)",
#             (bus_name.strip(), from_city.strip(), to_city.strip(), seats)
#         )
#         conn.commit()
#         return f"✅ Bus '{bus_name}' added with {seats} seats."
#     except ValueError:
#         return "❌ Total seats must be an integer."
#     except sqlite3.IntegrityError:
#         return "❌ That bus name already exists."

def add_bus(bus_name, from_city, to_city, total_seats):
    if not (bus_name and from_city and to_city):
        return "❌ All fields are required."

    try:
        seats = int(float(total_seats))  # Converts from float (from gr.Number) to int
        if seats <= 0:
            return "❌ Total seats must be a positive integer."

        cursor.execute(
            "INSERT INTO buses (bus_name, from_city, to_city, total_seats) VALUES (?, ?, ?, ?)",
            (bus_name.strip(), from_city.strip(), to_city.strip(), seats)
        )
        conn.commit()
        return f"✅ Bus '{bus_name}' added with {seats} seats."
    except (ValueError, TypeError):
        return "❌ Total seats must be a valid number."
    except sqlite3.IntegrityError:
        return "❌ That bus name already exists."


# helper to get list of buses for dropdown
def get_bus_choices():
    cursor.execute("SELECT bus_name FROM buses ORDER BY bus_name")
    return [row[0] for row in cursor.fetchall()]

# 3. Passenger: book a ticket
def book_ticket(passenger_name, bus_name, travel_date, seat_number):
    if not (passenger_name and bus_name and travel_date and seat_number):
        return "❌ All fields are required."
    try:
        seat = int(seat_number)
    except ValueError:
        return "❌ Seat number must be an integer."

    cursor.execute("SELECT id, total_seats FROM buses WHERE bus_name = ?", (bus_name,))
    bus = cursor.fetchone()
    if not bus:
        return "❌ Selected bus not found."
    bus_id, total_seats = bus
    if not (1 <= seat <= total_seats):
        return f"❌ Seat must be between 1 and {total_seats}."

    try:
        cursor.execute(
            "INSERT INTO tickets (passenger_name, bus_id, travel_date, seat_number) VALUES (?, ?, ?, ?)",
            (passenger_name.strip(), bus_id, travel_date.strip(), seat)
        )
        conn.commit()
        return f"✅ Ticket booked on '{bus_name}' for {travel_date}, Seat #{seat}."
    except sqlite3.IntegrityError:
        return "❌ That seat is already booked on that date."

# 4. View functions
def view_buses():
    buses = cursor.execute("SELECT bus_name, from_city, to_city, total_seats FROM buses").fetchall()
    if not buses:
        return "No buses available."
    return "\n".join([
        f"{b[0]}: {b[1]} → {b[2]} ({b[3]} seats)"
        for b in buses
    ])

def view_bookings():
    rows = cursor.execute('''
        SELECT t.id, t.passenger_name, b.bus_name, t.travel_date, t.seat_number
        FROM tickets t
        JOIN buses b ON t.bus_id = b.id
        ORDER BY t.travel_date, b.bus_name, t.seat_number
    ''').fetchall()
    if not rows:
        return "No bookings yet."
    return "\n".join([
        f"#{r[0]} {r[1]} → {r[2]} on {r[3]} (Seat {r[4]})"
        for r in rows
    ])

# 5. Build Gradio interface
with gr.Blocks() as app:
    gr.Markdown("## 🚌 Bus Ticket Booking System")

    # Admin tab
    with gr.Tab("➕ Add Bus"):
        name_in  = gr.Text(label="Bus Name")
        from_in  = gr.Text(label="From City")
        to_in    = gr.Text(label="To City")
        seats_in = gr.Number(label="Total Seats", precision=0)
        add_btn  = gr.Button("Add Bus")
        add_out  = gr.Textbox(label="Status")
        add_btn.click(add_bus, [name_in, from_in, to_in, seats_in], add_out)

    # View buses tab
    with gr.Tab("📄 View Buses"):
        show_buses = gr.Button("Show All Buses")
        buses_out  = gr.Textbox(label="Available Buses", lines=8)
        show_buses.click(view_buses, None, buses_out)

    # Booking tab
    with gr.Tab("🎫 Book Ticket"):
        passenger_in = gr.Text(label="Passenger Name")
        bus_dd       = gr.Dropdown(choices=get_bus_choices(), label="Select Bus")
        refresh_btn  = gr.Button("🔄 Refresh Bus List")
        refresh_btn.click(lambda: gr.update(choices=get_bus_choices()), None, bus_dd)

        date_in      = gr.Text(label="Travel Date (YYYY-MM-DD)")
        seat_in      = gr.Number(label="Seat Number", precision=0)
        book_btn     = gr.Button("Book Ticket")
        book_out     = gr.Textbox(label="Status")

        book_btn.click(book_ticket,
                       [passenger_in, bus_dd, date_in, seat_in],
                       book_out)

    # View bookings tab
    with gr.Tab("📋 View Bookings"):
        show_bookings = gr.Button("Show All Bookings")
        book_list     = gr.Textbox(label="Bookings", lines=10)
        show_bookings.click(view_bookings, None, book_list)

    app.launch()
