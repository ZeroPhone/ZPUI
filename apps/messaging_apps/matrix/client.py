from libs.matrix_client.matrix_client.client import MatrixClient
from libs.matrix_client.matrix_client.api import MatrixRequestError
from libs.matrix_client.matrix_client.user import User
from requests.exceptions import MissingSchema

from zpui_lib.helpers import setup_logger

logger = setup_logger(__name__, 'info')

class Client():

	def __init__(self, username, password=None, token=None, server="matrix.org"):

		self.username = username
		self.server = server
		self.server_url = "https://{}".format(self.server)
		self.token = None
		self.logged_in = True

		# Create the matrix client
		if token == None and password != None:
			self.matrix_client = MatrixClient(self.server_url)

			# Try logging in the user
			try:
				self.token = self.matrix_client.login(username=username, password=password)
				self.user = User(self.matrix_client, self.matrix_client.user_id)

			except MatrixRequestError as e:
				self.logged_in = False
				if e.code == 403:
					logger.exception("Wrong username or password")
				else:
					logger.exception("Check server details")

			except MissingSchema as e:
				logger.exception("Bad URL format")

		else:
			self.matrix_client = MatrixClient(self.server_url, token=token, user_id=username)
			self.user = User(self.matrix_client, self.matrix_client.user_id)

	# Return the user's display name
	def get_user_display_name(self):
		return self.user.get_display_name()

	# Get the rooms of the user
	def get_rooms(self):
		return self.matrix_client.rooms

	def get_user(self):
		return self.user

	def get_token(self):
		return self.token
