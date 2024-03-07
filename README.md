# Flask Chatroom
#### Video Demo:  <URL HERE>
> My final project for CS50, Harvard's introduction to Computer Science.

#### Overview
This project is a chatroom web app I developed with the Flask framework and Websockets (flask_socketio library). 

| Homepage |
| :---: |
| <img src="Screenshots/Homepage.png" width="400">

#### How It Works
This app allows you to send text messages to other people in a chatroom. To create a room, you must enter a name and, optionally, a room code. If you don't enter a room code and create, a random 4-character ASCII code will be generated.

In order to join a room, you must again enter a name and the room code corresponding to the room you want to join. Then you can click join and you will enter the chatroom.

| Chatroom |
| :---: |
| <img src="Screenshots/Chatroom.png" width="400">

Optionally, you may also choose to create an account via 'register'. Doing so will allow you to access the chatlogs of any rooms you have joined while you were logged in.

| Homepage When Logged In |
| :---: |
| <img src="Screenshots/HomeLoggedIn.png" width="400"> |

>February 7, 2024:
I will be developing a Flask chat application that will allow you to talk with people over the internet.

>March 3, 2024:
This application was developed for CS50X, Harvard's online introduction to computer science course. 
Please note that this application uses environment variables for the feedback sending aspect, so if
you would like to utilise that feature, you will have to make a .env file in the directory and add
your email and app password.
