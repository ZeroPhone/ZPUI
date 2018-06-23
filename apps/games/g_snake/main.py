from ui import Canvas
from time import sleep
from ui import DialogBox, ffs
from helpers import ExitHelper
from threading import Event, Lock
from random import randint

menu_name = "Snake"

i = None #Input device
o = None #Output device
do_exit = None

snake = [(10, 10), (11, 10), (12, 10)]
lose = False
direction = "right"
apple = False


def init_app(input, output):
	#Gets called when app is loaded
	global i, o, c
	i = input; o = output; c = Canvas(o)

	
def callback():
	#Gets called when app is selected from menu
	start_game()
	#pass

def avancer():
	snake.remove(snake[0])
	if direction == "right":
		snake.append((snake[-1][0]+1, snake[-1][1]))
	elif direction == "left":
		snake.append((snake[-1][0]-1, snake[-1][1]))
	elif direction == "down":
		snake.append((snake[-1][0], snake[-1][1]+1))
	else:
		snake.append((snake[-1][0], snake[-1][1]-1))


def set_keymap():
	keymap = {"KEY_LEFT": lambda:make_a_move("left"),
			  "KEY_RIGHT": lambda:make_a_move("right"),
			  "KEY_UP": lambda:make_a_move("up"),
			  "KEY_DOWN": lambda:make_a_move("down"),
			  "KEY_ENTER": confirm_exit}
	i.stop_listen()
	i.set_keymap(keymap)
	i.listen()

def confirm_exit():
	choices = ["y", "n"]
	choice = DialogBox(choices, i, o, message="Exit the game?").activate()
	if choice is True:
		do_exit.set()
	else:
		start_game()

def perdu():
	global lose
	for segment in snake:
		if not(0<segment[0]<128):
			lose = True
		if not(0<segment[1]<64):
			lose = True
	for segment in snake[:-1]:
		if snake[-1] == segment:
			lose = True

def eat():
	global snake, apple
	for segment in snake:
		if (segment[0] == applex and segment[1] == appley):
			apple = False
			liste = []
			liste.append(snake[0])
			liste.extend(snake)
			snake = liste

def start_game():
	global apple, lose, applex, appley, snake
	set_keymap()
	while(lose == False):
		c = Canvas(o)
		for segment in snake:
			c.point(segment)
		if apple == True:
			c.point((applex, appley))
		else :
			applex = randint(0,128)
			appley = randint(0,64)
			c.point((applex, appley))
			apple = True
		c.display() # Display the canvas on the screen
		avancer()
		eat()
		perdu()
		sleep(0.1)

def make_a_move(touche):
	global direction
	assert(touche in ["up", "down", "left", "right"])
	if (direction == "up" and touche == "down") or (direction == "down" and touche == "up") or (direction == "left" and touche == "right") or (direction == "right" and touche == "left"):
		pass
	else:
		direction = touche


