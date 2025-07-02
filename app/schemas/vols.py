from pydantic import BaseModel
from typing import Optional

# Modelo para la solicitud de vuelo
class AirlineImage(BaseModel):
    uri: str

class RouteInfo(BaseModel):
    origin: str
    originName: str
    destination: str
    destinationName: str
    departureTime: str
    arrivalTime: str
    terminal: str
    gate: str

class PassengerInfo(BaseModel):
    name: str
    seat: str
    ticketNumber: str

class FlightResponse(BaseModel):
    id: str
    airline: str
    airlineImage: AirlineImage
    flightNumber: str
    route: RouteInfo
    passenger: PassengerInfo
    boardingTime: str
    baggageAllowance: str
    qrCode: str

class CreateFlightRequest(BaseModel):
    flight_id: int
    seat: str
    ticket_number: str
    qr_code_link: str
