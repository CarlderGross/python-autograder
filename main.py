import subprocess
import os

assignmentPath = "FacsimileAssignment.zip"

if (not os.path.exists("Temp")):
    os.mkdir("Temp") #make the temp folder, if it doesn't exist already
    #this folder will be the destination of extracted files from the assignment
    
subprocess.run("tar -xf "+assignmentPath+" -C Temp")

#TODO: empty the temp folder after use