from icalendar import Calendar, Event
from datetime import datetime

def create_ics_file(flight_data, filename):
    cal = Calendar()

    for flight in flight_data:
        event = Event()
        event.add('summary', f"Flight: {flight['flight_number']}")
        event.add('description', f"Route: {flight['route']}\nClass: {flight['class']}\nTicket Type: {flight['ticket_type']}\nReservation Number: {flight['reservation_number']}\nConfirmation Number: {flight['confirmation_number']}")
        event.add('dtstart', datetime.strptime(flight['date'] + flight['departure_time'], '%m月%d日(木)%H:%M').replace(year=datetime.now().year))
        event.add('dtend', datetime.strptime(flight['date'] + flight['arrival_time'], '%m月%d日(木)%H:%M').replace(year=datetime.now().year))
        event.add('location', flight['route'])
        event.add('url', flight['seat_selection_link'])

        cal.add_component(event)

    with open(filename, 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    flight_data = [
        {
            "flight_number": "ANAI263",
            "route": "東京(羽田)→福岡",
            "date": "12月28日(木)",
            "departure_time": "16:25",
            "arrival_time": "18:30",
            "class": "普通席",
            "ticket_type": "ANA SUPER VALUE55",
            "reservation_number": "0595",
            "confirmation_number": "450-029-052",
            "seat_selection_link": "https://www.airtrip.jp/booking/confirm/getlink.php/?utm_source=email&utm_medium=boardingguidemail&utm_campaign=boardingguidemail"
        },
        {
            "flight_number": "ANA1076",
            "route": "福岡→東京(羽田)",
            "date": "01月04日(木)",
            "departure_time": "09:55",
            "arrival_time": "11:30",
            "class": "普通席",
            "ticket_type": "ANA SUPER VALUE55",
            "reservation_number": "0326",
            "confirmation_number": "227-077-106",
            "seat_selection_link": "https://www.airtrip.jp/booking/confirm/getlink.php/?utm_source=email&utm_medium=boardingguidemail&utm_campaign=boardingguidemail"
        }
    ]

    create_ics_file(flight_data, 'flight_schedule.ics')

