This is the COMP598 Project by
-Anmoljeet Gill, ID:260568705
-Brian Huynh, ID:260569992

####################################################################################
To start run python manager.py
This will launch the command window, there are now the following commands

-build
#build creates a image and either 

##1) can copy over a file located in the /myimages directory, arugment is the file name
--build copy [argument]
---ex: build copy script1

##2) can install a program onto the image like python-minimal or netcat, argument is the desired program
--build install [argument] 
---ex: build install python-minimal

##3) can do both, argument1 is the program to install, arugment2 is the file to copy over
--build both [argument1] [argument 2]
---ex: build both python-minimal script1

##4) can create a image with netcat with a exposed port as an arugment
--build netcat [arugment]
---ex: build netcat 80

-run
#run creates the container with a made image or one from the dockerhub
---ex: run -itd -p 80 image_1 nc -l -p 80
---ex: run -itd -p 80 nginx:alpine
-scale
#can create or delete replicas of a already running container
--scale [up/down] [# to inc/dec] [worker_name]
###This following commands will make 3 replicas of a container worker1 and then reduce the total copies of worker1 down to 2.
---ex: scale up 3 worker1
---ex: scale down 2 worker1

-stop
#this will stop the container and remove it from the fault tolerance as it is no longer desired.
--stop [worker_name]

-start
#this will start up a container that has been stopped and will allow it to be fault tolerant if it fails again.
--start [worker_name]

-list
#this will print out information of the containers (this is just docker ps -a)
--list

-recovery
#this is the manual command for having the manager restore crashed containers, this is not needed as the manager checks for crashes containers before and after every command and brings them back to function if they are desired to be fault tolerant.
--recovery

-quit
#this command clears the fault tolerance of all containers and shuts them down safely and turns off the proxy(nginx) and the network bridge.


