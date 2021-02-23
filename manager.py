import subprocess
import sys
import shlex
import pickle
import nginx
import os

#command to remove all containers that exited
#docker rm $(docker ps -a -f status=exited -q)
#command to kill all containers 
#docker rm $(docker ps -aq)
#command to remove all docker images
#docker system prune

###########################################################################
#gets the names of all docker containers and uses it as variable to check if they
# are running or not.
#docker inspect -f '{{.State.Running}}' $(docker inspect -f='{{.Name}}' $(docker ps -aq --no-trunc))
############################################################################
#old test code
#processEcho = subprocess.Popen(["echo","-e", "FROM busybox\nRUN echo \"hello worldo\"\nCOPY  lol.txt /usr/lol.txt"] , stdout = subprocess.PIPE)

#processEcho = subprocess.Popen(["echo","-e", "FROM ubuntu:latest\nCOPY script1 script1\n RUN chmod 777 script1"] , stdout = subprocess.PIPE)

############################################################################
#basic commands are build, run, stop, list, scale
#args[0] is script name
#args[1] will be the decider on what we do, make new worker, run worker, stop worker, list, scale, etc
#args[2] if empty is base image, if non empty is linux executable program(netcat, nginx)
#args[3] and beyond will be the variables for the command run worker 


############################################################################
#run -it -p 8080:8080 worker_1 /bin/bash -c "nc -l -p 8080; echo 'hello'


############################################################################
###store the data, pickle it and save it
#		data = ['LOL',10]
#		with open('data.pickle', 'wb') as f:
#			pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

###load the pickled data
#		with open('data.pickle' , 'rb' ) as f:
#			data = pickle.load(f)

#		print(data[0])

###########################################################################
def build(args,counter):
	processEcho = 0
	argsLen = len(args)

	if argsLen == 1: #checks if args[0] is empty

		processEcho = subprocess.Popen(["echo","-e", "FROM ubuntu"] , stdout = subprocess.PIPE)

		#processEcho = subprocess.Popen(["echo","-e", "FROM ubuntu:latest\nCOPY script1 script1\n RUN chmod 777 script1"] , stdout = subprocess.PIPE)


	else:
		if(args[1] == "netcat"):

			processEcho = subprocess.Popen(["echo","-e", "FROM ubuntu:latest\nRUN apt-get -y update\nRUN apt-get -y install net-tools\nRUN apt-get -y install netcat\nEXPOSE " + args[2]] , stdout = subprocess.PIPE)

		if (args[1] == "install"):
		
			processEcho = subprocess.Popen(["echo","-e", "FROM ubuntu:latest\nRUN apt-get -y update\nRUN apt-get -y install " + args[2]] , stdout = subprocess.PIPE)
		
		if (args[1] == "copy"):

			processEcho = subprocess.Popen(["echo","-e", "FROM ubuntu\nCOPY " + args[2] + " " + args[2] +"\n RUN chmod 777 "+ args[2]] , stdout = subprocess.PIPE)

		if (args[1] == "both"):

			processEcho = subprocess.Popen(["echo","-e", "FROM ubuntu\nRUN apt-get -y update\nRUN apt-get -y install " + args[2] +"\nCOPY " + args[3] + " " + args[3] +"\n RUN chmod 777 "+ args[3]] , stdout = subprocess.PIPE)

	processDocker = subprocess.Popen(["docker", "build", "-t", "image_"+str(counter), "-f-", 
"."], stdin = processEcho.stdout, stdout = subprocess.PIPE)

	output = processDocker.communicate()[0]

	print output
#############################################################################
def run(args):

	global conPicDict
	global workerCounter
	global firstTimeNginx
	global firstTimeNetcat
	global path

	#args[1] is image name
	#args[2] is container name
	#args[3]+ is the commands
	processDocker = subprocess.Popen(["docker","run","--name", "worker"+str(workerCounter)] + args[1:], stdout = subprocess.PIPE)

	output = processDocker.communicate()

	#connect container to network bridge conNet

	processNetConnect = subprocess.Popen(["docker","network","connect", "conNet","worker"+str(workerCounter)], stdout = subprocess.PIPE)

	output = processNetConnect.communicate()

	#get the image_name and the Cmds
	processCmd = subprocess.Popen(["docker", "inspect" ,"-f","'{{.Config.Cmd}}'", "worker"+str(workerCounter)], stdout = subprocess.PIPE)

	cmd = processCmd.communicate()[0]

	
	cmd = cmd.split("'")[1]
	processImageName = subprocess.Popen(["docker", "inspect" ,"-f","'{{.Config.Image}}'", "worker"+str(workerCounter)], stdout = subprocess.PIPE)

	imageName = processImageName.communicate()[0]
	imageName = imageName.split("'")[1]

	conPicDict["worker"+str(workerCounter)] = [imageName,cmd] + ["worker"+str(workerCounter)]

	conPicDict['count'] = workerCounter

	#everytime we run a container we add it to the load balancer by editing
	#the nginx.conf file then we have to kill, rm, rebuild and rerun loadBal


	#checks if its nginx or netcat(anything else)
	isNginx = False

	if(imageName == 'nginx:alpine'):

		isNginx = True

	#if both firstimes are false we add the server to both upstreams so it runs


	c = nginx.loadf(path+'/load-balancer/nginx.conf')
	HttpFilter = ((c.filter('Http')[0]))

	if(isNginx):

		if(firstTimeNginx == False):

			#make upstream make worker add worker to upstream add upstream
			#to the http
			nginxUpstream = nginx.Upstream('nginx')
			worker = nginx.Key('server', "worker"+str(workerCounter)+":80")
			nginxUpstream.add(worker)
			HttpFilter.add(nginxUpstream)

			#when we make upstream for first time we also make server server
			s = nginx.Server()
			s.add(nginx.Key('listen','8100'),nginx.Location('/' , nginx.Key('proxy_pass','http://nginx'), nginx.Key('proxy_redirect','off'),nginx.Key('proxy_set_header','Host $host'), nginx.Key('proxy_set_header','X-Real_IP $remote_addr'), nginx.Key('proxy_set_header','X-Forwarded-For $proxy_add_x_forwarded_for'), nginx.Key('proxy_set_header','X-Forwarded-Host $server_name')))
			HttpFilter.add(s)
			#dumping
			firstTimeNginx = True

			nginx.dumpf(c, path+'/load-balancer/nginx.conf')
		else:
			
			upstreamSearch = HttpFilter.filter('Upstream')
			j = 0
			found = False
			for key in upstreamSearch:
				if(((key.as_dict).keys())[0] == 'upstream nginx'):
					found = True		
					break
				j = j + 1

			worker = nginx.Key('server', "worker"+str(workerCounter)+":80")
			if(found):
				upstreamSearch[j].add(worker)

			nginx.dumpf(c, path+'/load-balancer/nginx.conf')

	else:

		if(firstTimeNetcat == False):

			#make upstream make worker add worker to upstream add upstream
			#to the http
			nginxUpstream = nginx.Upstream('netcat')
			worker = nginx.Key('server', "worker"+str(workerCounter)+":80")
			nginxUpstream.add(worker)
			HttpFilter.add(nginxUpstream)

			#when we make upstream for first time we also make server server
			s = nginx.Server()
			s.add(nginx.Key('listen','8101'),nginx.Location('/' , nginx.Key('proxy_pass','http://netcat'), nginx.Key('proxy_redirect','off'),nginx.Key('proxy_set_header','Host $host'), nginx.Key('proxy_set_header','X-Real_IP $remote_addr'), nginx.Key('proxy_set_header','X-Forwarded-For $proxy_add_x_forwarded_for'), nginx.Key('proxy_set_header','X-Forwarded-Host $server_name')))
			HttpFilter.add(s)
			#dumping
			firstTimeNetcat = True

			nginx.dumpf(c, path+'/load-balancer/nginx.conf')
		else:
			
			upstreamSearch = HttpFilter.filter('Upstream')
			j = 0
			found = False
			for key in upstreamSearch:
				if(((key.as_dict).keys())[0] == 'upstream netcat'):
					found = True		
					break
				j = j + 1

			worker = nginx.Key('server', "worker"+str(workerCounter)+":80")
			if(found):
				upstreamSearch[j].add(worker)

			nginx.dumpf(c, path+'/load-balancer/nginx.conf')



	#now kill,rm,build,run
	loadBalReset()

	#increment workerCounter
	workerCounter = workerCounter + 1
	#run -itd -p 8080 worker_1 nc -lk -p 8080
	#run -itd -p 80 nginx:alpine
#############################################################################
def loadBalReset():
	global path
	global conPicDict
	
	processKill = subprocess.Popen(["docker","kill","loadBal"], stdout = subprocess.PIPE)
	output = processKill.communicate()

	processRM = subprocess.Popen(["docker","rm","loadBal"], stdout = subprocess.PIPE)
	output = processRM.communicate()

	processBuild = subprocess.Popen(["docker","build", path+'/load-balancer',"-t","load-balancer"], stdout = subprocess.PIPE)
	output = processBuild.communicate()

	processRun = subprocess.Popen(["docker","run","--name","loadBal","-itd","--network=conNet","-p","8100:8100","-p","8101:8101","load-balancer"], stdout = subprocess.PIPE)
	output = processRun.communicate()

	processStart = subprocess.Popen(["docker","start","loadBal"], stdout = subprocess.PIPE)
	output = processStart.communicate()

	conPicDict["loadBal"] = ["docker","start","loadBal"]

##############################################################################
def stop(args):
	#only stop 1 worker at a time
	global conPicDict
	global firstTimeNginx
	global firstTimeNetcat
	global path

	processDocker = subprocess.Popen(["docker", "stop"]+ [args[1]], stdout = subprocess.PIPE)

	output = processDocker.communicate()

	#everytime we call stop we remove worker off nginx upstream list

	processImageName = subprocess.Popen(["docker", "inspect" ,"-f","'{{.Config.Image}}'", args[1]], stdout = subprocess.PIPE)

	imageName = processImageName.communicate()[0]
	imageName = imageName.split("'")[1]

	isNginx = False

	if(imageName == 'nginx:alpine'):

		isNginx = True

	c = nginx.loadf(path+'/load-balancer/nginx.conf')
	HttpFilter = ((c.filter('Http')[0]))

	upstreamSearch = HttpFilter.filter('Upstream')
	upstreamServer = ""

	j = 0
	found = False
	searchVar = ""

	if(isNginx):
		searchVar = 'upstream nginx'
	else:
		searchVar = 'upstream netcat'

	for key in upstreamSearch:
		if(((key.as_dict).keys())[0] == searchVar):
			found = True		
			break
		j = j + 1


	if(found):
		upstreamServer = upstreamSearch[j]

	#upstreamServer is our upstream server, z is the dict inside it

	z = upstreamServer.filter(nginx.Key,'server')

	#now u is a list of objects we need to go through each object and find out 		values then remove that value index from u and then return
	i = 0

	for key in z:
		x = (key.as_dict.values())[0]
		if (x == args[1]+":80"):
			break
		i = i + 1


	del z[i]
	upstreamServer.children = z
	
	#if the upstreamServer list is empty then we remove upstream server

	#checks if its empty as dict returns false if empty and true if filled

	if (not (upstreamServer.as_dict).get(searchVar)):
		(HttpFilter.children).remove(upstreamServer)

		#if remove upstream then we must remove server
		serverSearch = (HttpFilter.filter('Server'))
		serverServer = ""

		j = 0
		found = False
		searchVar = ""

		if(isNginx):
			searchVar = '8100'
			firstTimeNginx = False
		else:
			searchVar = '8101'
			firstTimeNetcat = False
		for key in serverSearch:
			if( (((key.children)[0]).as_dict).get('listen') == searchVar):
				found = True		
				break
			j = j + 1


		if(found):
			serverServer = serverSearch[j]

		(HttpFilter.children).remove(serverServer)

	nginx.dumpf(c, path+'/load-balancer/nginx.conf')
	
	#for key in (upstreamServer.filter(nginx.Key,'server')):
	#	print key.as_dict

	loadBalReset()

	#removing worker off the pickle dictionary of recovery
	keys = conPicDict.keys()

	#args[1] is gonna be the worker name, ex: worker1
	for key in keys: 

		if(key == args[1]):

			del conPicDict[key]
	
	#print output
	#run -itd -p 8080 worker_1 nc -lk -p 8080
############################################################################
def start(args):
	
	global path
	global conPicDict
	global firstTimeNginx
	global firstTimeNetcat

	processDocker = subprocess.Popen(["docker", "start"]+ [args[1]], stdout = subprocess.PIPE)

	output = processDocker.communicate()

	#get the image_name and the Cmds
	processCmd = subprocess.Popen(["docker", "inspect" ,"-f","'{{.Config.Cmd}}'", ""+ args[1]], stdout = subprocess.PIPE)

	cmd = processCmd.communicate()[0]
	cmd = cmd.split("'")[1]
	processImageName = subprocess.Popen(["docker", "inspect" ,"-f","'{{.Config.Image}}'", ""+ args[1]], stdout = subprocess.PIPE)

	imageName = processImageName.communicate()[0]
	imageName = imageName.split("'")[1]

	#conPicDict[args[1]] = ["docker","start"] + [args[1]]
	conPicDict[args[1]] = [imageName,cmd] + [args[1]]
	#args[1] is gonna be the worker name, ex: worker1

	isNginx = False

	if(imageName == 'nginx:alpine'):

		isNginx = True

	#if both firstimes are false we add the server to both upstreams so it runs


	c = nginx.loadf(path+'/load-balancer/nginx.conf')
	HttpFilter = ((c.filter('Http')[0]))

	if(isNginx):

		if(firstTimeNginx == False):

			#make upstream make worker add worker to upstream add upstream
			#to the http
			nginxUpstream = nginx.Upstream('nginx')
			worker = nginx.Key('server', args[1]+":80")
			nginxUpstream.add(worker)
			HttpFilter.add(nginxUpstream)

			#when we make upstream for first time we also make server server
			s = nginx.Server()
			s.add(nginx.Key('listen','8100'),nginx.Location('/' , nginx.Key('proxy_pass','http://nginx'), nginx.Key('proxy_redirect','off'),nginx.Key('proxy_set_header','Host $host'), nginx.Key('proxy_set_header','X-Real_IP $remote_addr'), nginx.Key('proxy_set_header','X-Forwarded-For $proxy_add_x_forwarded_for'), nginx.Key('proxy_set_header','X-Forwarded-Host $server_name')))
			HttpFilter.add(s)
			#dumping
			firstTimeNginx = True

			nginx.dumpf(c, path+'/load-balancer/nginx.conf')
		else:
			
			upstreamSearch = HttpFilter.filter('Upstream')
			j = 0
			found = False
			for key in upstreamSearch:
				if(((key.as_dict).keys())[0] == 'upstream nginx'):
					found = True		
					break
				j = j + 1

			worker = nginx.Key('server', args[1]+":80")
			if(found):
				upstreamSearch[j].add(worker)

			nginx.dumpf(c, path+'/load-balancer/nginx.conf')

	else:

		if(firstTimeNetcat == False):

			#make upstream make worker add worker to upstream add upstream
			#to the http
			nginxUpstream = nginx.Upstream('netcat')
			worker = nginx.Key('server', args[1]+":80")
			nginxUpstream.add(worker)
			HttpFilter.add(nginxUpstream)

			#when we make upstream for first time we also make server server
			s = nginx.Server()
			s.add(nginx.Key('listen','8101'),nginx.Location('/' , nginx.Key('proxy_pass','http://netcat'), nginx.Key('proxy_redirect','off'),nginx.Key('proxy_set_header','Host $host'), nginx.Key('proxy_set_header','X-Real_IP $remote_addr'), nginx.Key('proxy_set_header','X-Forwarded-For $proxy_add_x_forwarded_for'), nginx.Key('proxy_set_header','X-Forwarded-Host $server_name')))
			HttpFilter.add(s)
			#dumping
			firstTimeNetcat = True

			nginx.dumpf(c, path+'/load-balancer/nginx.conf')
		else:
			
			upstreamSearch = HttpFilter.filter('Upstream')
			j = 0
			found = False
			for key in upstreamSearch:
				if(((key.as_dict).keys())[0] == 'upstream netcat'):
					found = True		
					break
				j = j + 1

			worker = nginx.Key('server', args[1]+":80")
			if(found):
				upstreamSearch[j].add(worker)

			nginx.dumpf(c, path+'/load-balancer/nginx.conf')

	#now kill,rm,build,run
	loadBalReset()
	
	#print output

############################################################################
def listing():

	processDocker = subprocess.Popen(["docker", "ps" ,"-a"], stdout = subprocess.PIPE)

	output = processDocker.communicate()[0]
	
	print output

#############################################################################
def recovery():
	#keys without count so only workers
	global conPicDict
	keys = conPicDict.keys()

	
	for key in keys: 
		#if we get a key called count we skip it
		if(key == 'count'):
			continue
		
		processDocker = subprocess.Popen(["docker", "inspect" ,"-f","'{{.State.Running}}'", ""+ key], stdout = subprocess.PIPE)

		output = processDocker.communicate()[0]

		#output.split("'") looks like ['','true','\n']
		if(output.split("'")[1] == 'false'):
			#if we get false we want to restart worker

			processStarter = subprocess.Popen(["docker","start",key], stdout = subprocess.PIPE)
			outputStart = processStarter.communicate()[0]
			
#################################################################################
def scale(args):

	#to make scale work for netcat again we need to get rid of 
	global conPicDict
	#check the image and see if its ngix:alpine or something else
	processImageName = subprocess.Popen(["docker", "inspect" ,"-f","'{{.Config.Image}}'", ""+ args[3]], stdout = subprocess.PIPE)

	imageName = processImageName.communicate()[0]

	imageName = imageName.split("'")[1]

	if(imageName == 'nginx:alpine'):

		if(args[1] == "up"):
			#cant scale things with nextline or (')
			for x in range(int(args[2])):

				#use runlike to get the args of the containers run command
				string1 = "$(runlike " + args[3] + ")"
				processDocker = subprocess.Popen("echo " + string1, shell=True, stdout = subprocess.PIPE)

				output = processDocker.communicate()[0]
				listArgs = (output.splitlines()[0].split("'")[0]).split(" ")

				indices = [ i for i , s in enumerate(listArgs) if "hostname" in s]
				indicesRemove = [ i for i , s in enumerate(listArgs) if "label" in s]
				#just find the -p
				indicesPort = [ i for i , s in enumerate(listArgs) if "-p" in s]

				listArgs = [x.lower() for x in listArgs]

				run(["run"]+listArgs[(indicesPort[0]):indicesRemove[0]-1]+listArgs[(indicesRemove[0]+5):len(listArgs)-1] +["daemon off;"])
			
		if(args[1] == "down"):


			#gets the args of the docker container we are asking to scale down
			string1 = "$(runlike " + args[3] + ")"
			processDocker = subprocess.Popen("echo " + string1, shell=True, stdout = subprocess.PIPE)

			output = processDocker.communicate()[0]
			listArgs = (output.splitlines()[0].split("'")[0]).split(" ")
			indices = [ i for i , s in enumerate(listArgs) if "hostname" in s]
			indicesRemove = [ i for i , s in enumerate(listArgs) if "label" in s]

			indicesPort = [ i for i , s in enumerate(listArgs) if "-p" in s]

			listArgs = [x.lower() for x in listArgs]

			compareVal = listArgs[(indicesPort[0]):indicesRemove[0]-1]+listArgs[(indicesRemove[0]+5):len(listArgs)-1] +["daemon off;"]

			#for each key in the recovery Dict, we do runlike and get args if 
			#args are the same we do stop and rm
			#do this until count is = to number we want to remove and stop

			count = 0

			listnames = []
			for key in conPicDict:

				if(count == int(args[2])):
					break
				if(key != "count" and key != "loadBal" and conPicDict.get(key)[0] == imageName):
				#use runlike to get the args of the containers run command
					string1 = "$(runlike " + key + ")"
					processDocker = subprocess.Popen("echo " + string1, shell=True, stdout = subprocess.PIPE)

					output = processDocker.communicate()[0]
					listArgsCompare = (output.splitlines()[0].split("'")[0]).split(" ")

					indices = [ i for i , s in enumerate(listArgsCompare) if "hostname" in s]

					indicesPort = [ i for i , s in enumerate(listArgsCompare) if "-p" in s]

					indicesRemove = [ i for i , s in enumerate(listArgsCompare) if "label" in s]
					listArgsCompare = [x.lower() for x in listArgsCompare]

					Val = listArgsCompare[(indicesPort[0]):indicesRemove[0]-1]+listArgsCompare[(indicesRemove[0]+5):len(listArgsCompare)-1] +["daemon off;"]


					if(compareVal == Val):
						indices = [ i for i , s in enumerate(listArgsCompare) if "name" in s]
						workerName = (listArgsCompare[indices[0]].split("="))[1]

						listnames.append(workerName)
						count = count + 1
						

			for name in listnames:
				stop(["stop"]+[name])
				
				processRM = subprocess.Popen(["docker", "rm" ,""+ name], stdout = subprocess.PIPE)

				output = processRM.communicate()[0]	

	
	#if its not nginx:alpine just do whatever
	else:
	
		if(args[1] == "up"):
			#cant scale things with nextline or (')
			for x in range(int(args[2])):

				#use runlike to get the args of the containers run command
				string1 = "$(runlike " + args[3] + ")"
				processDocker = subprocess.Popen("echo " + string1, shell=True, stdout = subprocess.PIPE)

				output = processDocker.communicate()[0]
				listArgs = (output.splitlines()[0].split("'")[0]).split(" ")

				indices = [ i for i , s in enumerate(listArgs) if "hostname" in s]

				#just find the -p
				indicesPort = [ i for i , s in enumerate(listArgs) if "-p" in s]

				listArgs = [x.lower() for x in listArgs]

				run(["run"]+listArgs[(indicesPort[0]):])
			
		if(args[1] == "down"):


			#gets the args of the docker container we are asking to scale down
			string1 = "$(runlike " + args[3] + ")"
			processDocker = subprocess.Popen("echo " + string1, shell=True, stdout = subprocess.PIPE)

			output = processDocker.communicate()[0]
			listArgs = (output.splitlines()[0].split("'")[0]).split(" ")
			indices = [ i for i , s in enumerate(listArgs) if "hostname" in s]
			indicesPort = [ i for i , s in enumerate(listArgs) if "-p" in s]

			listArgs = [x.lower() for x in listArgs]

			compareVal = listArgs[(indicesPort[0]):]

			#for each key in the recovery Dict, we do runlike and get args if 
			#args are the same we do stop and rm
			#do this until count is = to number we want to remove and stop

			count = 0

			listnames = []
			for key in conPicDict:
				if(count == int(args[2])):
					break
				if(key != "count" and key != "loadBal"  and conPicDict.get(key)[0] == imageName):
				#use runlike to get the args of the containers run command
					string1 = "$(runlike " + key + ")"
					processDocker = subprocess.Popen("echo " + string1, shell=True, stdout = subprocess.PIPE)

					output = processDocker.communicate()[0]
					listArgsCompare = (output.splitlines()[0].split("'")[0]).split(" ")
					indices = [ i for i , s in enumerate(listArgsCompare) if "hostname" in s]
					indicesPort = [ i for i , s in enumerate(listArgsCompare) if "-p" in s]
					listArgsCompare = [x.lower() for x in listArgsCompare]
					

					Val = listArgs[(indicesPort[0]):]


					if(compareVal == Val):
						indices = [ i for i , s in enumerate(listArgsCompare) if "name" in s]
						workerName = (listArgsCompare[indices[0]].split("="))[1]

						listnames.append(workerName)
						count = count + 1
						

			for name in listnames:
				stop(["stop"]+[name])
				
				processRM = subprocess.Popen(["docker", "rm" ,""+ name], stdout = subprocess.PIPE)

				output = processRM.communicate()[0]


	#run -itd -p 80 nginx:alpine
	#run -itd -p 8080 image_1 nc -lk -p 8080
#################################################################################
def main():

	global conPicDict
	global workerCounter

	#firstTime has happened then True if not yet then False
	global firstTimeNginx
	global firstTimeNetcat
	global path

	path = os.getcwd()
	print path
	firstTimeNginx = False
	firstTimeNetcat = False
	conPicDict = {}
	#making Linux Bridge




	with open('data.pickle' , 'rb') as f:
		conPicDict = pickle.load(f)

	imageCounter = 1

	#checks if there are old workers if so then update counter to the correct #
	workerCounter = 1


	if (conPicDict.get('count') != None):
		workerCounter = conPicDict.get('count') + 1
	
	if (workerCounter == 1):

		processBridge = subprocess.Popen(["docker", "network", "create", "--driver","bridge","conNet"], stdout = subprocess.PIPE)

		output = processBridge.communicate()
	#conPicDict is the dictionary that is storing the run commands
	#the key is the workerCounter (worker+str(workerCounter))
	#key "count" is how many workers there are operating.

	#load up the conPicDict


	while True: 
		with open('data.pickle', 'wb') as f:				    				pickle.dump(conPicDict, f, pickle.HIGHEST_PROTOCOL)
		
		#do recovery all the time
		recovery()

		command_input = raw_input("Enter Command: ")
		args = shlex.split(command_input)
		
		#recovery before and after input
		recovery()

		if (len(args) == 0):
			continue

		if (args[0] == "build"):
			build(args,imageCounter)
			imageCounter = imageCounter + 1
			
		if (args[0] == "run"):
			run(args)

		if (args[0] == "scale"):
			scale(args)

		if (args[0] == "stop"):
			stop(args)

		if (args[0] == "start"):
			start(args)

		if (args[0] == "list"):
			listing()

		if (args[0] == 'recovery'):
			recovery()

		if (args[0] == "quit"):


			
	
			###kills the containers and rms them.
			keys = conPicDict.keys()

			for key in keys: 

				if(key == 'count'):
					continue

				processKill = subprocess.Popen(["docker", "kill" ,""+ key], stdout = subprocess.PIPE)

				output = processKill.communicate()[0]

				processRM = subprocess.Popen(["docker", "rm" ,""+ key], stdout = subprocess.PIPE)

				output = processRM.communicate()[0]

			#kills the networkBridge
			processOldBridgeRemove = subprocess.Popen(["docker", "network", "rm","conNet"], stdout = subprocess.PIPE)

			output = processOldBridgeRemove.communicate()	
		
			#wiping clean the pickle file
			
			emptyDict = {}
			with open('data.pickle', 'wb') as f:
				pickle.dump(emptyDict, f, pickle.HIGHEST_PROTOCOL)

			#wipe clean the nginx.conf file for the upstream portion



			c = nginx.loadf(path+'/load-balancer/nginx.conf')
			httpBlock = (c.filter('Http')[0])
			#upNetcat = (c.filter('Http')[0]).filter('Upstream')[1]
			z = []

			#now u is a list of objects we need to go through each object and find out 		values then remove that value index from u and then return
			

			httpBlock.children = z
			#upNetcat.children = z

			nginx.dumpf(c, path+'/load-balancer/nginx.conf')


			sys.exit()

	#run -itd -p 8080 worker_1 nc -lk -p 8080

if __name__ == "__main__":

	main()














