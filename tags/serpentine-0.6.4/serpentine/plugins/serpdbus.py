"""This creates associates a number of D-Bus services to serpentine."""
import dbus
from serpentine import services

class SerpentineDbus (object):
	def __init__ (self):
		bus = dbus.SessionBus ()
		dbus_srv = bus.get_service ("org.freedesktop.DBus")
		dbus_obj = dbus_srv.get_object ("/org/freedesktop/DBus", "org.freedesktop.DBus")
		if services.SERVICE_NAME in dbus_obj.ListServices ():
			raise SerpentineError("Serpentine is already running.")
		
		# Start the service since it isn't available
		#self.__service = dbus.Service (services.SERVICE_NAME, bus=bus)
		#self.__manager = services.Manager (self.__service, self)
